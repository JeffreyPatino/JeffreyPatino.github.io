---
title: "Coldcard RNG Entropy Failure: C Preprocessor Traps"
subtitle: Dissecting a $70M hardware wallet vulnerability caused by macro logic traps and leaky abstractions.
date: 2026-08-07
slug: coldcard-rng-entropy-failure
reading_time: 10 min
tags:
  - Security
  - C
  - Python
  - MicroPython
  - Systems Engineering
  - Cryptography
summary: A look into the Coldcard RNG entropy collapse, tracing how a C preprocessor directive mismatch and refactored API calls caused a silent fallback to a non-cryptographic PRNG.
---

## The Problem

In cryptocurrency hardware wallets, entropy generation is the foundation of security. When generating a BIP-39 master seed, the underlying system needs to sample true physical random noise (TRNG) from hardware registers and secure elements.

In Coldcard hardware wallets (Mk3 and subsequent revisions), a silent failure in the random number generator (RNG) pipeline caused device entropy to drop from 128 bits down to about 40 bits (~1.1 trillion total key combinations). This allowed automated on-chain attackers to brute-force private keys offline and drain over $70 million USD in BTC across 1,196 wallets in under 41 minutes.

This wasn't a failure of the hardware itself. It was a software integration issue: a refactored Python API call routed execution into an upstream C library, where a macro logic guard mismatch (`#ifndef` vs `#if`) silently triggered a non-cryptographic software fallback algorithm (Yasmarang).

## The Investigation

To figure out how clean-looking code refactoring led to this collapse, we can trace the execution across four files spanning three system layers:

1. **High-Level Application Layer (`shared/random.py`)**: Python application code managed by Coinkite.
2. **Board Configuration (`stm32/COLDCARD/mpconfigboard.h`)**: C board-level macros specifying hardware drivers.
3. **C Bridge Library (`libngu/rng.c`)**: "Never Give Up" (libngu) abstraction layer bridging MicroPython to hardware crypto bindings.
4. **Upstream MicroPython Engine (`ports/stm32/rng.c`)**: Low-level STM32 microcontroller drivers and software PRNG fallbacks.

| Layer / Component | File | Language | Owner / Module | Purpose |
| --- | --- | --- | --- | --- |
| **High-Level API** | `shared/random.py` | Python | Coinkite | Generates 32-byte seed arrays for BIP-39 wallet creation. |
| **Board Config** | `stm32/COLDCARD/mpconfigboard.h` | C Header | Coinkite | Board-specific hardware configuration header for MicroPython. |
| **C Bridge Library** | `libngu/rng.c` | C Library | Coinkite Submodule | Binding wrapper bridging Python to low-level C libraries. |
| **Upstream Core** | `ports/stm32/rng.c` | C | MicroPython Core | Low-level STM32 hardware driver engine and software PRNG fallback. |

By following the call stack from Python down to low-level C preprocessor evaluation, we can isolate the exact conditions that bypassed the hardware TRNG register sampling.

## Code Breakdown

### 1. Board Configuration (`mpconfigboard.h`)

To prevent MicroPython's native STM32 hardware driver from colliding with Coinkite's custom multi-source hardware RNG driver (`ckcc.rng_bytes`), developers disabled MicroPython's built-in driver in the board configuration header:

```c
// stm32/COLDCARD/mpconfigboard.h
#define MICROPY_HW_ENABLE_RNG (0)
```

The developer's intent here was clear: "Do not compile MicroPython's default hardware driver."

### 2. The Logic Guard Trap (`libngu/rng.c`)

To prevent building firmware without a hardware TRNG, a safety assertion was placed in the bridge layer:

```c
// libngu/rng.c
#ifndef MICROPY_HW_ENABLE_RNG
  #error "get a HW TRNG plz"  // Compiler safety guard
#endif

#define CHIP_TRNG_32() rng_get()
```

Here lies the critical preprocessor trap: `#ifndef MACRO` checks for macro **existence** in the symbol table, regardless of its evaluated numerical value. Because `#define MICROPY_HW_ENABLE_RNG (0)` was present in the header, `#ifndef` evaluated to `False` ("The macro IS defined"). The compiler suppressed the `#error` directive and built the binary successfully.

### 3. MicroPython Core Logic & Silent Fallback (`ports/stm32/rng.c`)

When `libngu` called MicroPython's internal `rng_get()` function, MicroPython evaluated the exact same configuration macro using a value-based directive:

```c
// ports/stm32/rng.c
uint32_t rng_get(void) {
    #if MICROPY_HW_ENABLE_RNG
        // 1. SAFE PATH: Read physical noise from STM32 silicon registers
        RNG->CR |= RNG_CR_RNGEN;
        while (!(RNG->SR & RNG_SR_DRDY)) { ... }
        return RNG->DR;
    #else
        // 2. SILENT FALLBACK: Non-cryptographic Yasmarang Software PRNG
        return yasmarang_rand();
    #endif
}
```

Because `#if MICROPY_HW_ENABLE_RNG` evaluates the numerical value `0`, it evaluated to `False`. Control flow dropped silently into the `#else` block, returning output from `yasmarang_rand()`, a deterministic software PRNG seeded with low-cardinality chip serial numbers (`UID_low32`) and boot timers (`SysTick->VAL` and `RTC->TR`).

### 4. The Refactoring Commit (`shared/random.py`)

Prior to March 2021, Coldcard firmware invoked the custom hardware driver directly:

```python
# Firmware <= v3.2.2 (SAFE - Invoked custom C hardware driver directly)
seed = bytearray(32)
ckcc.rng_bytes(seed)
```

In commit `b18723dd`, the call was refactored to standard Python idioms:

```python
# Firmware >= v4.0.0 (VULNERABLE - Triggered Macro Trap)
seed = random.bytes(32)
```

This high-level change looked clean in code review, but it diverted seed generation away from the custom hardware driver directly into MicroPython's `rng_get()`, hitting the `#if 0` preprocessor trap.

---

## Architectural Questions

### Q1: Why set `#define MICROPY_HW_ENABLE_RNG (0)` in the configuration file?

1. **Overriding Cascading Defaults (`mpconfigport.h`):** MicroPython uses a hierarchical C header configuration architecture. The target port header (`mpconfigport.h`) defines default values if a board header doesn't explicitly specify them:
```c
#ifndef MICROPY_HW_ENABLE_RNG
  #define MICROPY_HW_ENABLE_RNG (1)  // MicroPython default: ON
#endif
```
If Coinkite had omitted `#define MICROPY_HW_ENABLE_RNG` from `mpconfigboard.h`, MicroPython's build system would have automatically assigned it `1`.

2. **Preventing Peripheral Conflicts:** Coinkite built a custom multi-source RNG driver (`ckcc.rng_bytes`) that directly managed the STM32 physical TRNG registers and an external ATECC608A Secure Element. If MicroPython's built-in driver remained enabled (`1`), both drivers would compete to enable clocks (`RNG_CR_RNGEN`), read registers, and reset hardware states. Setting the macro to `(0)` was intended to cleanly disable MicroPython's default driver.

### Q2: What called the default driver prior to the `random.bytes()` refactor?

* **Firmware <= v3.2.2:** Nothing called MicroPython's default driver. High-level code called `ckcc.rng_bytes(seed)`, which executed Coinkite's custom C module directly, mixing raw STM32 register noise with Secure Element entropy and bypassing MicroPython's `rng.c`.
* **The Refactoring Illusion:** When developers introduced `random.bytes(32)`, they assumed it acted as a standard wrapper that would call their custom driver underneath. Instead, `random.bytes(32)` invoked `rng_get()`, which fell straight into Yasmarang.

### Q3: What happens at compile time when set to `(1)` vs. `(0)`?

Setting `#define MICROPY_HW_ENABLE_RNG (0)` did not delete `rng_get()` or create a missing symbol error. It swapped the internal implementation of the function at compile time:

| State / Behavior | `#define MICROPY_HW_ENABLE_RNG (1)` | `#define MICROPY_HW_ENABLE_RNG (0)` (Coldcard State) |
| --- | --- | --- |
| **Is `rng_get()` compiled into binary?** | **Yes** | **Yes** |
| **Is `rng_get()` callable by Python?** | **Yes** | **Yes** |
| **Hardware Driver Included?** | **Yes** (Reads physical silicon registers) | **No** (Stripped by C preprocessor) |
| **Software Fallback Included?** | **No** (Stripped by C preprocessor) | **Yes** (Executed on every function call) |
| **Output of `random.bytes(32)`** | Cryptographic Hardware Randomness | 40-bit Pseudorandom Software Output |

Had MicroPython wrapped the entire `rng_get()` function signature inside `#if MICROPY_HW_ENABLE_RNG`, setting the macro to `0` would have completely erased `rng_get()`. The compiler would have thrown an `undefined reference to 'rng_get'` error during the March 2021 refactor.

### Q4: Upstream Runtime vs. High-Assurance Product Responsibilities

* **MicroPython Design:** In general IoT microcontrollers, silent fallbacks ("failing soft") prevent `import random` from crashing on low-end hardware. However, in cryptographic engineering, systems must **fail closed**.
* **Coinkite Responsibility:** Coinkite built a high-security wallet appliance on top of a general-purpose runtime. Writing an existence-based `#ifndef` check instead of a value-based `#if` check neutered their compiler guard. Furthermore, calling `random.bytes(32)` orphaned their custom Secure Element driver.

---

## The Fix

### Corrected Preprocessor Guard (`libngu/rng.c`)

```c
// ❌ INCORRECT: Checks existence only; passes when defined as (0)
#ifndef MICROPY_HW_ENABLE_RNG
  #error "get a HW TRNG plz"
#endif

// ✅ CORRECT: Checks existence AND numeric value
#if !defined(MICROPY_HW_ENABLE_RNG) || (MICROPY_HW_ENABLE_RNG == 0)
  #error "Hardware TRNG is explicitly disabled or missing in configuration!"
#endif
```

### Fail-Closed Driver Assertion (`ports/stm32/rng.c`)

```c
uint32_t rng_get(void) {
    #if defined(MICROPY_HW_ENABLE_RNG) && (MICROPY_HW_ENABLE_RNG != 0)
        RNG->CR |= RNG_CR_RNGEN;
        while (!(RNG->SR & RNG_SR_DRDY)) { ... }
        return RNG->DR;
    #else
        #error "Critical: Cannot execute rng_get() without physical hardware TRNG!"
    #endif
}
```

---

## The White-Hat Rescue Problem

If a bug like this allows deterministic key derivation offline, white-hat groups (like SEAL911) will often try to calculate the vulnerable addresses first. Their goal is to sweep the funds into secure multi-signature escrows using high miner fees or private relays to hold the funds safely for the victims. 

But this introduces a massive challenge: **Proving ownership.**

When a key derivation algorithm is broken, the weak key is publicly derivable. Anyone (victim or attacker) can sign a message using that compromised key. Standard signature verification completely fails as proof of ownership. 

```text
【 Standard Crypto Model 】
Private Key  ════════════════════════► Ownership Proof

【 Weak-Entropy Rescue Model 】
Compromised Key ═════════════════════► INVALID (Anyone has it)

Funding Source (Address B) ──┐
Exchange Withdrawal Logs   ──┼───────► Valid Provenance Proof
HD xpub / Passphrase Data  ──┤
Pre-Incident Artifacts     ──┘
```

To verify who actually owns the rescued funds, white-hats have to rely on alternative proofs:
1. **Funding Provenance:** The claimant must prove control over the original funding source (Address B) that sent funds to the vulnerable address years prior. This might involve signing a message from Address B or providing signed API withdrawal receipts from a KYC exchange.
2. **HD Derivation Artifacts:** Providing metadata not visible on-chain, such as the exact custom BIP-39 passphrase, non-standard derivation paths, or root `xpub` structures.
3. **Pre-Exploit Signatures:** Providing off-chain signatures or message logs created using the vulnerable address *before* the exploit happened.

---

## Takeaways

1. **The Visual Entropy Fallback Trap:** Unlike database connections that throw exceptions on failure, pseudo-random number generators do not crash when they fail. A 40-bit software PRNG returns 32 bytes of plausible-looking data that generates valid-looking 12-word seed phrases. Without output entropy health assertions, data corruption occurs silently.
2. **Leaky Standard Library Abstractions:** Replacing `ckcc.rng_bytes()` with `random.bytes(32)` was intended as a clean-code refactor. In C/Python hybrids, replacing an explicit driver call with a generic library function can silently drop execution into unexpected fallbacks.
3. **Orphaned Security Architecture:** Switching to `random.bytes(32)` orphaned Coinkite's multi-source entropy mixer (which XORed STM32 TRNG with Secure Element entropy), leaving security hardware compiled in the binary but completely uncalled.
4. **C Preprocessor Safety Rules:** `#ifndef MACRO` evaluates existence; `#if MACRO` evaluates numeric value. Combining `#ifndef` checks with `#define MACRO (0)` configuration flags is an anti-pattern that neuters compiler guard checks. Use `-Wundef` to force compiler errors on uninitialized or ambiguous macro evaluations.
5. **Continuous Integration & Mock Register Assertions:** Incorporate register-access assertions in unit testing frameworks (e.g. Unity or CMock) to verify that physical silicon registers are touched during seed generation:
```c
void test_seed_generation_accesses_hardware_trng(void) {
    mock_stm32_rng_register_read_count = 0;
    generate_wallet_seed();
    TEST_ASSERT_GREATER_THAN(0, mock_stm32_rng_register_read_count); 
}
```

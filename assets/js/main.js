/*==================== MENU SHOW Y HIDDEN ====================*/
const navMenu = document.getElementById("nav-menu"),
      navToggle = document.getElementById("nav-toggle"),
      navClose = document.getElementById("nav-close")

/*===== MENU SHOW =====*/
/* Validate if constant exists */
if (navToggle) {
    navToggle.addEventListener("click", () => {
        navMenu.classList.add("show-menu")
    })
}

/*===== MENU HIDDEN =====*/
/* Validate if constant exists */
if (navClose) {
    navClose.addEventListener("click", () => {
        navMenu.classList.remove("show-menu")
    })
}

/*==================== REMOVE MENU MOBILE ====================*/
const navLink = document.querySelectorAll(".nav__link")

function linkAction() {
    const navMenu = document.getElementById("nav-menu")
    // When we click on each nav__link, we remove the show-menu class
    navMenu.classList.remove("show-menu")
}
navLink.forEach(n => n.addEventListener("click", linkAction))

/*==================== EXPERIENCE TABS ====================*/
const tabs = document.querySelectorAll("[data-target]"),
      tabContents = document.querySelectorAll("[data-content]")

tabs.forEach(tab => {
    tab.addEventListener("click", () => {
        const target = document.querySelector(tab.dataset.target)

        tabContents.forEach(tabContent => {
            tabContent.classList.remove("experience__active")
        })
        target.classList.add("experience__active")

        tabs.forEach(tab => {
            tab.classList.remove("experience__active")
        })
        tab.classList.add("experience__active")
    })
})

/*==================== SCROLL SECTIONS ACTIVE LINK ====================*/
const sections = document.querySelectorAll("section[id]");

function scrollActive() {
  const scrollY = window.pageYOffset

  sections.forEach((current) => {
    const sectionHeight = current.offsetHeight
    const sectionTop = current.offsetTop - 50
    sectionId = current.getAttribute("id")

    if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
      document
        .querySelector(".nav__menu a[href*=" + sectionId + "]")
        .classList.add("active-link")
    } else {
      document
        .querySelector(".nav__menu a[href*=" + sectionId + "]")
        .classList.remove("active-link")
    }
  })
}
window.addEventListener("scroll", scrollActive);

/*==================== CHANGE BACKGROUND HEADER ====================*/ 
function scrollHeader() {
    const nav = document.getElementById("header")
    // When the scroll is greater than 200 viewport height, add the scroll-header class to the header tag
    if (this.scrollY >= 80) nav.classList.add("scroll-header")
    else nav.classList.remove("scroll-header")
  }
  window.addEventListener("scroll", scrollHeader)

/*==================== SHOW SCROLL UP ====================*/ 
function scrollUp() {
    const scrollUp = document.getElementById("scroll-up")
    // When the scroll is higher than 560 viewport height, add the show-scroll class to the a tag with the scroll-top class
    if (this.scrollY >= 560) scrollUp.classList.add("show-scroll")
    else scrollUp.classList.remove("show-scroll")
  }
  window.addEventListener("scroll", scrollUp)

/*==================== DARK LIGHT THEME ====================*/
const themeButton = document.getElementById("theme-button")
const darkTheme = "dark-theme"
const iconTheme = "uil-sun"

// Previously selected topic (if user selected)
const selectedTheme = localStorage.getItem("selected-theme")
const selectedIcon = localStorage.getItem("selected-icon")

// We obtain the current theme that the interface has by validating the dark-theme class
const getCurrentTheme = () => document.body.classList.contains(darkTheme) ? "dark" : "light"
const getCurrentIcon = () => themeButton.classList.contains(iconTheme) ? "uil-moon" : "uil-sun"

// We validate if the user previously chose a topic
if (selectedTheme) {
  // If the validation is fulfilled, we ask what the issue was to know if we activated or deactivated the dark
  document.body.classList[selectedTheme === "dark" ? "add" : "remove"](darkTheme)
  themeButton.classList[selectedIcon === "uil-moon" ? "add" : "remove"](iconTheme)
}

// Activate / deactivate the theme manually with the button
themeButton.addEventListener("click", () => {
    // Add or remove the dark / icon theme
    document.body.classList.toggle(darkTheme)
    themeButton.classList.toggle(iconTheme)
    // We save the theme and the current icon that the user chose
    localStorage.setItem("selected-theme", getCurrentTheme())
    localStorage.setItem("selected-icon", getCurrentIcon())
})

document.getElementById('contact-form').addEventListener('submit', async function(event) {
  event.preventDefault();

  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  try {
    const response = await fetch('https://personal-website.jeffreypatino.workers.dev/email', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (response.ok) {
      alert('Your message has been sent successfully!');
      form.reset();
    } else {
      alert('There was an error sending your message. Please try again later.');
    }
  } catch (error) {
    console.error('Form submission failed:', error);
    alert('An unexpected error occurred. Please try again.');
  }
});

/*==================== CHATBOT ====================*/
const chatbotIcon = document.getElementById('chatbot-icon');
const chatbotBox = document.getElementById('chatbot-box');
const chatbotClose = document.getElementById('chatbot-close');
const chatbotMessages = document.getElementById('chatbot-messages');
const chatbotInput = document.getElementById('chatbot-input-field');
const chatbotSend = document.getElementById('chatbot-send');

// Toggle chatbot
chatbotIcon.addEventListener('click', () => {
    chatbotBox.classList.toggle('active');
});

chatbotClose.addEventListener('click', () => {
    chatbotBox.classList.remove('active');
});

// Send message function
async function sendMessage() {
    const message = chatbotInput.value.trim();
    if (message === '') return;

    // Add user message
    const userMessageDiv = document.createElement('div');
    userMessageDiv.classList.add('message', 'user-message');
    userMessageDiv.textContent = message;
    chatbotMessages.appendChild(userMessageDiv);

    // Clear input
    chatbotInput.value = '';

    // Auto-scroll to bottom
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

    try {
        const response = await fetch('https://personal-website.jeffreypatino.workers.dev/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: message
            }),
        });

        // Create bot response
        const botMessageDiv = document.createElement('div');
        botMessageDiv.classList.add('message', 'bot-message');

        if (response.ok) {
            const data = await response.json();
            botMessageDiv.textContent = data.message || data.response || "Message received!";
        } else {
            const errorData = await response.json().catch(() => ({}));
            botMessageDiv.textContent = errorData.message || "Sorry, there was an error sending your message. Please try the contact form.";
        }

        chatbotMessages.appendChild(botMessageDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    } catch (error) {
        console.error('Message sending failed:', error);
        const botMessageDiv = document.createElement('div');
        botMessageDiv.classList.add('message', 'bot-message');
        botMessageDiv.textContent = "Sorry, there was an error sending your message. Please try the contact form above.";
        chatbotMessages.appendChild(botMessageDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }
}

// Send message on button click
chatbotSend.addEventListener('click', sendMessage);

// Send message on Enter key
chatbotInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
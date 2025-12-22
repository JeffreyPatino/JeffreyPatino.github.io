# Development Notes

This document tracks the inspiration, resources, and progress made during the development of this portfolio project.

## Inspiration & Design
The design and layout of this portfolio were inspired by the following creators and developers:
* [Brittany Chiang](https://brittanychiang.com/) – Clean, high-end design patterns and navigation.
* [vgaidarji.me](http://vgaidarji.me/#blog) – Content structure and blog layout.
* [Bedimcode](https://www.youtube.com/watch?v=27JtRAI3QO8) – Modern UI components and responsive styling.

## Project Progress
### Completed Tasks
- [x] **Portfolio Imagery**: Updated and optimized all personal project photos.
- [x] **Experience Section**: Consolidated "Education" and "Work History" into a single, unified "Experience" timeline for better flow.
- [x] **Contact Backend**: Successfully connected the contact form to a functional backend using Formspree.
- [x] **Mobile UX Fix**: Resolved the overlap issue between the chatbot and the "scroll up" icon on mobile devices.

### Form Backend Research
To keep the site static while maintaining functionality, I explored several methods for the "Contact Me" form:
* **Formspree**: [View Plans](https://formspree.io/plans) / [Implementation Guide](https://www.youtube.com/watch?v=vc9rgFHr098).
* **AWS Serverless**: Researched using AWS Lambda, API Gateway, and SES for a custom solution.
* **DataFire**: Explored as an alternative for connecting static sites to simple backends.

---

## Resolved Issues & Debugging Notes

| Issue | Resolution |
| :--- | :--- |
| **CORS Errors** | Implemented an `OPTIONS` preflight handler in the Worker to permit cross-origin requests from the `github.io` domain. |
| **Resend "From" Address** | Must match the `EMAIL_RECEIVER` secret exactly as verified in the Resend dashboard. |
| **Gemini 400 Error** | Payload parameters (like `temperature`) must be nested under `generationConfig`, not `config`. |
| **Gemini Auth Header** | Google expects the header `x-goog-api-key` (standard `key` or `Authorization` headers fail). |
| **URL Mapping** | Attempting to add a custom domain to a `github.io` zone in Cloudflare fails; use the default Worker domain with a professional slug instead. |

---

## Resources & Standards
### Development Tools
* **Responsive Testing**: [Website Planet Responsive Checker](https://www.websiteplanet.com/webtools/responsive-checker/) (Used for post-deployment verification).
* **Reference Code**: [Ratheshan03's Responsive Portfolio](https://github.com/Ratheshan03/Responsive-Portfolio-Design).

### Best Practices & Conventions
To maintain a clean and professional repository, I followed these standards:
* **Git Branching**: Followed the [Pixolo Naming Conventions](https://medium.com/@abhay.pixolo/naming-conventions-for-git-branches-a-cheatsheet-8549feca2534) (e.g., `feat/`, `fix/`, `docs/`).
* **Commit Messages**: Adhered to [Conventional Commits](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13) to ensure a readable project history.

---
*Updated: 2025*

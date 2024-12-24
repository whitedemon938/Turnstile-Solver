<div align="center">
 
  <h2 align="center">Cloudflare - Turnstile Solver</h2>
  <p align="center">
A Python-based solution for solving Cloudflare Turnstile challenges quickly (4-6 seconds solve time). The script uses patchright library to interact with web pages and solve the challenges with optimized browser management.
    <br />
    <br />
    <a href="https://discord.cyberious.xyz">💬 Discord</a>
    ·
    <a href="https://github.com/sexfrance/Turnstile-Solver#-changelog">📜 ChangeLog</a>
    ·
    <a href="https://github.com/sexfrance/Turnstile-Solver/issues">⚠️ Report Bug</a>
    ·
    <a href="https://github.com/sexfrance/Turnstile-Solver/issues">💡 Request Feature</a>
  </p>
</div>

### ⚙️ Installation

- Requires: `Python 3.8+`
- Make a python virtual environment: `python3 -m venv venv`
- Source the environment: `venv\Scripts\activate` (Windows) / `source venv/bin/activate` (macOS, Linux)
- Install the requirements: `pip install -r requirements.txt`
- Install chrominium: `patchright install chromium` / `python -m patchright install chromium`
- Start: `python main.py` to access all solvers through an interactive interface

---

### 🔥 Features

- **Multi-Browser Pool System**: Manages a pool of up to 10 browsers for concurrent solving
- **Page Pooling**: Efficient page reuse and management within each browser instance
- **Three Solving Modes**:
  - Synchronous solver for simple use cases
  - Asynchronous solver for better performance
  - API server for web-based integrations
- **Resource Optimization**: Smart browser and page lifecycle management
- **Debug Logging**: Detailed debug logs for troubleshooting
- **Cookie Support**: Ability to set custom cookies for authentication
- **Automatic Cleanup**: Proper resource management and cleanup
- **Interactive Interface**: Easy-to-use command-line interface to access all solvers
- **API Documentation**: Built-in web interface with API usage documentation
- **Invisible & Visible Support**: Works with both invisible and visible Turnstile challenges
- **Error Handling**: Comprehensive error handling and reporting

---

#### 📹 Preview

![Preview](https://i.imgur.com/YI6RZ5P.gif)

---

### ❗ Disclaimers

- I am not responsible for anything that may happen, such as API Blocking, IP ban, etc.
- This was a quick project that was made for fun and personal use if you want to see further updates, star the repo & create an "issue" [here](https://github.com/sexfrance/Turnstile-Solver/issues/)

---

### 📜 ChangeLog

```diff
v0.0.1 ⋮ 21/10/2024
! Initial release

v0.0.2 ⋮ 10/28/2024
! Modified the script, page.html is now in the scripts
! Made it faster and less resource intensive
! Modified the sync logic and made an async version
! Implemented logmagix logging
! Added timer

v0.0.3 ⋮ 11/7/2024
+ Added API server implementation
+ Added web interface for API documentation
+ Improved error handling and logging
+ Added concurrent processing support

v0.0.4 ⋮ 12/7/2024
+ Minor bug fixes
+ Added invisible cloudflare support
+ Removed headless option as it is not useful
+ Added cookie support for authentication

v0.0.5 ⋮ 12/24/2024
+ Implemented browser pooling system (10 concurrent browsers)
+ Added page pooling for each browser
+ Improved resource management
+ Added interactive CLI interface
+ Enhanced error handling and debugging
+ Optimized browser lifecycle management
```

---

<p align="center">
  <img src="https://img.shields.io/github/license/Theyka/Turnstile-Solver.svg?style=for-the-badge&labelColor=black&color=f429ff&logo=IOTA"/>
  <img src="https://img.shields.io/github/stars/Theyka/Turnstile-Solver.svg?style=for-the-badge&labelColor=black&color=f429ff&logo=IOTA"/>
  <img src="https://img.shields.io/github/languages/top/Theyka/Turnstile-Solver.svg?style=for-the-badge&labelColor=black&color=f429ff&logo=python"/>
</p>

Inspired by [Turnaround](https://github.com/Body-Alhoha/turnaround)
Original code by [Theyka](https://github.com/Theyka/Turnstile-Solver)
Changes by [Sexfrance](https://github.com/sexfrance)

<div align="center">
 
  <h2 align="center">Cloudflare - Turnstile Solver</h2>
  <p align="center">
A Python-based solution for solving Cloudflare Turnstile challenges quickly (4-6 seconds solve time). The script uses patchright library to interact with web pages and solve the challenges with optimized browser management.
    <br />
    <br />
    <a href="https://discord.cyberious.xyz">💬 Discord</a>
    ·
    <a href="#-changelog">📜 ChangeLog</a>
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
- **Browser Configuration**:
  - Headless mode support with user agent customization
  - Automated browser cleanup and session management
  - Custom user agent support for better stealth
- **Resource Optimization**:
  - Smart browser and page lifecycle management
  - Efficient memory usage and cleanup
  - Automatic resource scaling
- **Advanced Features**:
  - Cookie support for authentication
  - Custom action and cdata parameters
  - Invisible & visible challenge support
  - Comprehensive error handling
- **Developer Tools**:
  - Debug logging system
  - Interactive CLI interface
  - Built-in API documentation
  - Performance metrics tracking

---

#### 📹 Preview

![Preview](https://i.imgur.com/YI6RZ5P.gif)

---

### 🚀 Usage Examples

```python
# Synchronous Usage
from sync_solver import get_turnstile_token

result = get_turnstile_token(
    url="https://example.com",
    sitekey="your-site-key",
    invisible=True,
    headless=True,
    user_agent="Mozilla/5.0 ..."
)

# Asynchronous Usage
from async_solver import get_turnstile_token
import asyncio

async def main():
    result = await get_turnstile_token(
        url="https://example.com",
        sitekey="your-site-key",
        invisible=True,
        headless=True,
        user_agent="Mozilla/5.0 ..."
    )

# API Server Usage
curl "http://localhost:5000/turnstile?url=https://example.com&sitekey=your-site-key&invisible=true&headless=true&useragent=Mozilla/5.0..."
```

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
+ Added cookie support for authentication
+ Added action and cdata parameter support
+ Enhanced invisible Turnstile support
+ Improved browser management

v0.0.5 ⋮ 12/24/2024
+ Implemented browser pooling system
+ Added page pooling for each browser
+ Enhanced browser stealth features
+ Added headless mode with user agent support
+ Improved resource cleanup and management
+ Added comprehensive error handling
+ Optimized browser lifecycle management

v0.0.6 ⋮ 12/31/2024
+ Added custom user agent support
+ Enhanced headless mode stability
+ Improved browser argument handling
+ Added automatic scaling for resources
+ Enhanced error reporting system
+ Optimized page cleanup process
```

---

<p align="center">
  <img src="https://img.shields.io/github/license/sexfrance/Turnstile-Solver.svg?style=for-the-badge&labelColor=black&color=f429ff&logo=IOTA"/>
  <img src="https://img.shields.io/github/stars/sexfrance/Turnstile-Solver.svg?style=for-the-badge&labelColor=black&color=f429ff&logo=IOTA"/>
  <img src="https://img.shields.io/github/languages/top/sexfrance/Turnstile-Solver.svg?style=for-the-badge&labelColor=black&color=f429ff&logo=python"/>
</p>

Inspired by [Turnaround](https://github.com/Body-Alhoha/turnaround)
Original code by [Theyka](https://github.com/Theyka/Turnstile-Solver)
Changes by [Sexfrance](https://github.com/sexfrance)

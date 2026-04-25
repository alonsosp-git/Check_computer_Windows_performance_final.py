
# INSTRUCTIONS – How to run the Python script

First time only (install dependencies):
pip install -r requirements.txt


Every time you want to run the app:
streamlit run Check_computer_Windows_performance_final.py

********************************************************************************************
<img width="1887" height="940" alt="image" src="https://github.com/user-attachments/assets/cd1b02a6-e9b6-45f7-b6fd-671a30fcd365" />



# 🖥️ Enhanced Real-Time System Monitor - Complete Guide

## 📋 Overview

A comprehensive Windows system monitoring application built with Streamlit that provides real-time insights into your computer's performance, hardware health, network status, and system maintenance tools. This application features 15 specialized tabs, each designed to monitor and manage different aspects of your Windows system.

---

## 🎨 Application Features

### **Theme Support**
- Light, Dark, and Auto themes available
- Changes apply instantly (single click)
- Located in sidebar for easy access

### **Main Navigation**
15 tabs organized across the top of the application:
- 📊 Overview
- ⚡ Processes
- 📈 Performance Charts
- 🚀 Startup Apps
- 🔧 Advanced Tools
- 🌐 Network Tools
- 📝 Event Viewer
- 📂 Recent Activity
- 🌡️ Hardware Monitor
- 🔋 Battery & Power
- 🔔 Alerts & Logs
- 🏃 Benchmarks
- 💻 System Info
- 🔌 Network Connections
- ⚙️ Services & Tasks

---

## 📊 Tab 1: Overview

**Purpose:** Provides a quick snapshot of overall system health with animated gauges and key metrics.

**Features:**
- **System Metrics Cards:**
  - CPU usage percentage
  - Memory usage percentage
  - Disk usage percentage
  - Network usage (sent/received data)
  - System uptime
  - Active process count

- **Animated Gauges (3 visual gauges):**
  - CPU Usage gauge (0-100%) with color zones:
    - Green: 0-50% (normal)
    - Yellow: 50-80% (moderate)
    - Red: 80-100% (high)
  - Memory Usage gauge with same color coding
  - Disk Usage gauge with adjusted thresholds:
    - Green: 0-70%
    - Yellow: 70-90%
    - Red: 90-100%

- **Quick Actions:**
  - System information display
  - Uptime tracking
  - Process count monitoring

**Update Method:** Click "🔄 Refresh Now" button in sidebar to update all metrics and gauges.

---

## ⚡ Tab 2: Processes

**Purpose:** Monitor and manage running processes on your system.

**Features:**
- **Process List Table:**
  - Process ID (PID)
  - Process Name
  - CPU usage per process
  - Memory usage per process
  - Status (running/sleeping/etc.)

- **Sorting and Filtering:**
  - Sort by any column
  - Search/filter processes by name
  - View detailed process information

- **Process Management:**
  - View process details
  - Monitor resource consumption by process
  - Identify high CPU/memory consumers

**Use Cases:**
- Finding which program is using the most CPU
- Identifying memory-hungry applications
- Monitoring background processes

---

## 📈 Tab 3: Performance Charts

**Purpose:** Visualize system performance over time with interactive charts.

**Features:**
- **Historical Performance Graphs:**
  - CPU usage over time (line chart)
  - Memory usage trends
  - Disk I/O activity
  - Network throughput

- **Chart Types:**
  - Line charts for trends
  - Area charts for cumulative data
  - Interactive Plotly charts (zoom, pan, hover for details)

- **Time Windows:**
  - View performance over different time periods
  - Track performance patterns
  - Identify peak usage times

**Use Cases:**
- Monitoring system performance during specific tasks
- Identifying performance bottlenecks
- Tracking resource usage patterns

---

## 🚀 Tab 4: Startup Apps

**Purpose:** View and manage applications that run automatically when Windows starts.

**Features:**
- **Startup Applications List:**
  - Application name
  - Publisher
  - Status (enabled/disabled)
  - Impact on startup time

- **Quick Access Buttons:**
  - "Open Startup Apps (Settings)" - Opens Windows Settings > Startup
  - "Open Task Manager (Startup tab)" - Opens Task Manager for detailed management

**Use Cases:**
- Reviewing what starts with Windows
- Speeding up boot time by managing startup apps
- Identifying unnecessary startup programs

---

## 🔧 Tab 5: Advanced Tools

**Purpose:** System maintenance and optimization tools.

**Features:**

### **Cache Cleanup Tools:**
- **Clear Temp Files** - Removes temporary files from Windows Temp folder
  - Shows files removed count
  - Displays folder size
  - Safe deletion (skips locked files)

- **Clear Chrome Cache** - Cleans Chrome browser cache
  - Location: `%LocalAppData%\Google\Chrome\User Data\Default\Cache`

- **Clear Teams Cache** - Removes Microsoft Teams cache files
  - Teams cache folder
  - Teams chat cache
  - Teams local storage

- **Clear All Caches** - One-click cleanup of all above caches
  - Combined cleanup report
  - Total files removed count

### **Storage Analyzer (Python-based):**
- "Analyze Folder Sizes" button
  - Scans user's home directory (`C:\Users\YourName\`)
  - Shows folders larger than 10MB
  - Displays results in sortable table
  - Optional Plotly treemap visualization
  - Completion time: 2-5 seconds

### **Disk Information:**
- Disk volumes display via PowerShell
  - Drive letters
  - Capacity
  - Free space
  - Health status

### **Disk Fragmentation Analysis (C:):**
- "Analyze C: (elevated)" - Opens elevated command window for defrag analysis
- "Optimize C: (defrag /O)" - Runs disk optimization (requires elevation)
- "Open Defragmentation GUI (dfrgui)" - Opens Windows defrag tool

### **System Integrity Tools:**
- **Run chkdsk C:** - Opens elevated CMD to check disk errors
- **Run sfc /scannow** - System File Checker (elevated)
- **Analyze Component Store (DISM)** - Check Windows component store
- **Run DISM StartComponentCleanup** - Clean up Windows components
- **Windows Update Cleanup** - Opens Disk Cleanup for Windows Update files

### **System Information:**
- System uptime with color coding:
  - 🟢 Green: < 100 hours
  - 🟡 Yellow: 100-200 hours
  - 🔴 Red: > 200 hours
- Battery status and percentage (for laptops)

**Use Cases:**
- Freeing up disk space
- Improving system performance
- Maintaining disk health
- Finding large folders consuming space

---

## 🌐 Tab 6: Network Tools

**Purpose:** Monitor network status and perform network diagnostics.

**Features:**

### **Network Information:**
- **Public IP & ISP Information:**
  - Your public IP address
  - ISP (Internet Service Provider)
  - City, Region, Country
  - Retrieved via ipinfo.io API

- **DNS Servers:**
  - Primary and secondary DNS servers
  - Parsed from `ipconfig /all` output

- **Network Adapters:**
  - Adapter name
  - IPv4 address
  - Default gateway
  - Media state (connected/disconnected)

- **Internet Reachability:**
  - Tests connection to 8.8.8.8:53
  - Shows online/offline status

### **Network Commands:**
- "Flush DNS (ipconfig /flushdns)" - Clears DNS cache
- "Reset IP (netsh int ip reset)" - Resets TCP/IP stack (elevated)
- "Reset Winsock (netsh winsock reset)" - Resets Winsock catalog (elevated)
- "ipconfig /release" - Releases current IP
- "ipconfig /renew" - Requests new IP from DHCP

### **Network Interface Statistics:**
- Bytes sent/received
- Packets sent/received
- Error counts
- Drop counts

### **Speedtest (Internet Speed Test):**

**Setup:**
1. Click "🔍 Discover Speedtest Servers" button
   - Finds nearby speedtest servers
   - Shows server list with location and distance
   - Sorted by proximity

2. **Server Selection:**
   - Dropdown menu to choose server
   - "Auto (Best Server)" option available
   - Shows server location

3. **Test Configuration:**
   - Iterations slider (1-5 runs for averaging)
   - More iterations = more accurate results

4. Click "⚡ Run Speedtest" button
   - Performs download speed test
   - Performs upload speed test
   - Measures ping latency

5. **Results Display:**
   - Download speed (Mbps)
   - Upload speed (Mbps)
   - Ping (ms)
   - Shows Min/Max/Average for multiple iterations
   - Results in tabular format

**Auto-Installer:**
- If speedtest-cli not installed
- Click "Install speedtest-cli" button
- Automatic installation via pip
- Page refreshes when complete

**Use Cases:**
- Testing internet connection speed
- Diagnosing network issues
- Comparing ISP performance
- Verifying advertised speeds

---

## 📝 Tab 7: Event Viewer

**Purpose:** View and export Windows system error logs.

**Features:**

### **Event Log Selection:**
- **Available Logs:**
  - Application
  - System
  - Security
  - Setup
  - ForwardedEvents

- **Filters:**
  - Time window (0-1440 minutes)
  - Maximum events to fetch (10-5000)
  - Error level only (filters out warnings and info)

### **Event Display:**
- "🔁 Refresh Events" button
  - Queries Windows Event Log via PowerShell
  - Retrieves error-level events only
  - Groups events by log type

- **Event Tables (grouped by log):**
  - Application — Errors (separate table)
  - System — Errors (separate table)
  - Security — Errors (if any)
  - Setup — Errors (if any)
  - ForwardedEvents — Errors (if any)

- **Event Information Displayed:**
  - Time Created
  - Source (Provider Name)
  - Event ID
  - Level (Error)
  - Message

### **Export Functionality:**
- "📥 Download events as CSV" button
  - Exports all displayed events
  - CSV format with all columns
  - Sorted by log name and time
  - Filename: event_errors_grouped.csv

### **Quick Actions:**
- "Open Event Viewer (eventvwr)" - Opens Windows Event Viewer application
  - Uses elevated access
  - UAC prompt appears
  - Full Event Viewer interface

- "Refresh table" - Reloads the current view

**Use Cases:**
- Troubleshooting system errors
- Identifying recurring issues
- Exporting error logs for support tickets
- Monitoring application crashes

---

## 📂 Tab 8: Recent Activity

**Purpose:** Track recently modified and created files on your system.

**Features:**

### **File Activity Monitoring:**
- **Scan Configuration:**
  - Time range selection:
    - Past Day
    - Past Week
  - Activity type:
    - Modified files
    - Created files
  
- **Scan Scope:**
  - Scans user's home directory only (`C:\Users\YourName\`)
  - Max depth: 2 folders deep
  - Limit: 100 most recent files
  - Fast completion: 2-5 seconds

- "Scan for Files" button
  - Initiates file scan
  - Shows progress during scan
  - Displays results in table

### **Results Display:**
- **File Information Table:**
  - File name
  - Full file path
  - File size
  - Last modified date
  - File extension

- **Sorting and Filtering:**
  - Sort by date, name, or size
  - Search/filter results
  - View full paths

**Use Cases:**
- Finding recently downloaded files
- Tracking document changes
- Locating newly created files
- Reviewing recent file activity

---

## 🌡️ Tab 9: Hardware Monitor

**Purpose:** Monitor hardware temperatures, GPU status, and system sensors.

**Features:**

### **CPU Temperature:**
- **Display (when sensors available):**
  - CPU package temperature
  - Individual sensor readings
  - High temperature thresholds
  - Color-coded status:
    - 🟢 < 60°C (good)
    - 🟡 60-80°C (warm)
    - 🔴 > 80°C (hot)

- **When Not Available:**
  - Shows "Temperature sensors not available"
  - "🚀 Auto-Install WMI Module" button
    - One-click installation
    - Installs WMI + pywin32
    - Handles pip installation if missing
    - Auto-refreshes page when complete
  
  - Expandable guide for OpenHardwareMonitor:
    - Download link
    - Setup instructions
    - Explains benefits (all sensors, no install, portable)

### **GPU Status:**
- **Display (when NVIDIA GPU detected):**
  - GPU name (e.g., "NVIDIA GeForce RTX 3060")
  - Temperature with color coding
  - GPU load percentage
  - Memory usage (used/total MB)
  - Progress bar for load

- **When Not Available:**
  - Shows "GPU not detected"
  - "🚀 Auto-Install GPUtil (one click)" button
    - Automatic GPUtil installation
    - Handles pip installation if missing
    - Multiple installation methods
    - Auto-refreshes when complete
    - Timeout protection (120 seconds)

- **Smart Messages:**
  - If GPUtil installed but no NVIDIA GPU:
    - "✅ GPUtil installed, but no NVIDIA GPU detected"
    - "Note: GPUtil only supports NVIDIA GPUs"
    - "If you have AMD/Intel GPU, it won't be detected"

### **System Fans:**
- **Fan Speed Display (when OpenHardwareMonitor running):**
  - Fan names
  - RPM (rotations per minute)
  - Multiple fan sensors

- **CPU Frequency (always available):**
  - Current frequency (MHz)
  - Minimum frequency
  - Maximum frequency

### **Hardware Monitoring Status Panel:**
3-column status display showing:

- **GPUtil Module:**
  - ✅ Installed (green) or ⚠️ Not installed (yellow)
  - Instructions to click auto-install button

- **WMI Module:**
  - ✅ Installed or ⚠️ Not installed
  - Instructions to click auto-install button

- **OpenHardwareMonitor:**
  - ✅ Running with sensor count (e.g., "245 sensors")
  - ⚠️ Not running with download link

### **CPU Core Usage:**
- **Bar Chart Display:**
  - Usage percentage per CPU core
  - Individual core monitoring
  - Visual bar chart (Plotly)
  - Identifies which cores are working hardest

**Auto-Installation Features:**
- **Automatic pip handling** - Installs pip if missing
- **Multiple fallback methods** - Tries different installation approaches
- **Progress indicators** - Shows installation status
- **Error handling** - Clear error messages if installation fails
- **Auto-refresh** - Page reloads automatically after successful install

**Use Cases:**
- Monitoring CPU temperatures during heavy loads
- Checking GPU performance while gaming
- Ensuring proper cooling system function
- Identifying overheating issues
- Monitoring per-core CPU usage

---

## 🔋 Tab 10: Battery & Power

**Purpose:** Monitor laptop battery status and power management.

**Features:**

### **Battery Information (Laptops):**
- Battery percentage
- Charging status (charging/discharging/plugged in)
- Time remaining estimate
- Battery health

### **Power Plan:**
- Current active power plan
- Power mode status

### **Battery History:**
- Battery level over time
- Charge/discharge patterns

**Use Cases:**
- Monitoring laptop battery health
- Tracking battery drain rate
- Checking charging status
- Power management optimization

---

## 🔔 Tab 11: Alerts & Logs

**Purpose:** Configure system alerts and view alert history.

**Features:**

### **Alert Thresholds:**
- CPU usage threshold (configurable %)
- Memory usage threshold
- Disk usage threshold
- Temperature threshold
- Battery threshold

### **Alert Manager:**
- Alert history log
- Alert notifications
- Threshold breach tracking

### **Alert Types:**
- Performance alerts
- Hardware alerts
- Resource alerts

**Use Cases:**
- Getting notified of high resource usage
- Monitoring system health proactively
- Tracking alert patterns

---

## 🏃 Tab 12: Benchmarks

**Purpose:** Test system performance with various benchmarks.

**Features:**

### **CPU Benchmark:**
- Mathematical calculations
- Multi-core performance
- Single-core performance

### **Memory Benchmark:**
- Memory read/write speed
- Memory latency

### **Disk Benchmark:**
- Read/write speeds
- Sequential vs random access

### **Benchmark Results:**
- Performance scores
- Comparison with typical values
- Historical benchmark data

**Use Cases:**
- Testing system performance
- Comparing hardware upgrades
- Identifying performance bottlenecks

---

## 💻 Tab 13: System Info

**Purpose:** Detailed system information and specifications.

**Features:**

### **System Details:**
- OS version and build
- Computer name
- Processor information
- RAM total/available
- Motherboard information

### **Hardware Specifications:**
- CPU model and speed
- Number of cores/threads
- RAM type and speed
- Storage devices

### **Software Information:**
- Windows version
- System architecture (32/64-bit)
- Installation date

**Use Cases:**
- Quick reference for system specs
- Checking compatibility for software
- System inventory

---

## 🔌 Tab 14: Network Connections

**Purpose:** View active network connections and ports.

**Features:**

### **Active Connections:**
- Local address and port
- Remote address and port
- Connection status
- Protocol (TCP/UDP)
- Process using the connection

### **Connection Monitoring:**
- Established connections
- Listening ports
- Connection states

**Use Cases:**
- Monitoring network activity
- Identifying unexpected connections
- Troubleshooting network applications

---

## ⚙️ Tab 15: Services & Tasks

**Purpose:** View and manage Windows services and scheduled tasks.

**Features:**

### **Windows Services:**
- Service name
- Display name
- Status (running/stopped)
- Startup type

### **Scheduled Tasks:**
- Task name
- Status
- Last run time
- Next run time

**Use Cases:**
- Checking service status
- Viewing scheduled tasks
- System maintenance planning

---

## 🔄 Refresh & Update

**Sidebar Controls:**
- "🔄 Refresh Now" button
  - Updates all metrics
  - Refreshes gauges
  - Reloads data across all tabs
  - Manual update only (no auto-refresh to prevent freezing)

---

## 💾 Data & Privacy

- All monitoring is local (no data sent externally)
- Network tools use ipinfo.io for public IP only
- No data collection or tracking
- All file operations are safe (no deletions without confirmation)

---

## ⚙️ Technical Requirements

**Required Modules:**
- streamlit
- psutil
- pandas
- plotly (optional, for charts)

**Optional Modules (auto-installable):**
- gputil (GPU monitoring - NVIDIA only)
- wmi (temperature sensors)
- pywin32 (Windows integration)
- speedtest-cli (internet speed tests)

**System Requirements:**
- Windows 10 or Windows 11
- Python 3.8 or higher
- Administrator privileges (for some features)

---

## 🎯 Quick Start

1. Run the application:
   ```bash
   streamlit run System_Monitor_FINAL_FIXED.py
   ```

2. Select theme from sidebar (Light/Dark/Auto)

3. Navigate using tabs at the top

4. For hardware monitoring:
   - Click auto-install buttons as needed
   - One-click setup for GPUtil and WMI

5. Use "🔄 Refresh Now" to update metrics

---

## 📝 Notes

- Some features require administrator privileges
- UAC prompts will appear for elevated operations
- Auto-installers handle all dependencies
- Clear status indicators show what's installed
- No manual command-line setup needed

---

**Version:** Final
**Platform:** Windows
**Status:** Production Ready

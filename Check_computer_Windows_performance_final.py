# Copyright (c) 2025 Luis Salas — MIT License
# https://github.com/alonsosp-git/Check_computer_Windows_performance_final.py
# Enhanced System Monitor - Full Featured Version
# Run with: streamlit run enhanced_system_monitor.py

import streamlit as st
import psutil
import pandas as pd
import platform
import subprocess
import os
import time
import tempfile
import json
import urllib.request
import socket
import shutil
import re
import csv as _csv
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import hashlib
import io

# Windows-specific imports
try:
    import winreg
    WINDOWS = True
except ImportError:
    WINDOWS = False

# Optional imports with fallbacks
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except:
    PLOTLY_AVAILABLE = False

try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except:
    NOTIFICATIONS_AVAILABLE = False

# ============================================================================
# DATABASE SETUP FOR HISTORICAL DATA
# ============================================================================

class MetricsDatabase:
    def __init__(self, db_path='system_metrics.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        """Create tables for storing metrics"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                network_sent REAL,
                network_recv REAL,
                temperature REAL,
                battery_percent REAL
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT,
                message TEXT,
                severity TEXT
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS benchmarks (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                benchmark_type TEXT,
                score REAL,
                details TEXT
            )
        ''')
        
        self.conn.commit()
    
    def log_metrics(self, metrics):
        """Store current metrics"""
        try:
            self.conn.execute('''
                INSERT INTO metrics (cpu_percent, memory_percent, disk_percent, 
                                   network_sent, network_recv, temperature, battery_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (metrics.get('cpu', 0), metrics.get('memory', 0), 
                  metrics.get('disk', 0), metrics.get('net_sent', 0), 
                  metrics.get('net_recv', 0), metrics.get('temp', 0),
                  metrics.get('battery', 0)))
            self.conn.commit()
        except Exception as e:
            st.error(f"Database error: {e}")
    
    def get_historical_data(self, hours=24):
        """Retrieve historical metrics"""
        try:
            query = f'''
                SELECT * FROM metrics 
                WHERE timestamp > datetime('now', '-{hours} hours')
                ORDER BY timestamp
            '''
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def log_alert(self, alert_type, message, severity='warning'):
        """Log an alert"""
        try:
            self.conn.execute('''
                INSERT INTO alerts (alert_type, message, severity)
                VALUES (?, ?, ?)
            ''', (alert_type, message, severity))
            self.conn.commit()
        except:
            pass
    
    def get_alerts(self, hours=24):
        """Get recent alerts"""
        try:
            query = f'''
                SELECT * FROM alerts 
                WHERE timestamp > datetime('now', '-{hours} hours')
                ORDER BY timestamp DESC
            '''
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def log_benchmark(self, benchmark_type, score, details=''):
        """Log benchmark result"""
        try:
            self.conn.execute('''
                INSERT INTO benchmarks (benchmark_type, score, details)
                VALUES (?, ?, ?)
            ''', (benchmark_type, score, details))
            self.conn.commit()
        except:
            pass
    
    def get_benchmarks(self):
        """Get benchmark history"""
        try:
            query = 'SELECT * FROM benchmarks ORDER BY timestamp DESC LIMIT 100'
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()

# Initialize database
if 'db' not in st.session_state:
    st.session_state.db = MetricsDatabase()

# ============================================================================
# ALERT MANAGER
# ============================================================================

class AlertManager:
    def __init__(self):
        if 'alert_thresholds' not in st.session_state:
            st.session_state.alert_thresholds = {
                'cpu': 80,
                'memory': 85,
                'disk': 90,
                'temperature': 80,
                'battery': 20
            }
        
        if 'alerts_enabled' not in st.session_state:
            st.session_state.alerts_enabled = True
    
    def check_thresholds(self, metrics):
        """Check if any metrics exceed thresholds"""
        if not st.session_state.alerts_enabled:
            return []
        
        alerts = []
        thresholds = st.session_state.alert_thresholds
        
        if metrics.get('cpu', 0) > thresholds['cpu']:
            msg = f"High CPU Usage: {metrics['cpu']:.1f}%"
            alerts.append(('cpu', msg, 'warning'))
            self.send_notification('High CPU Usage', msg)
        
        if metrics.get('memory', 0) > thresholds['memory']:
            msg = f"High Memory Usage: {metrics['memory']:.1f}%"
            alerts.append(('memory', msg, 'warning'))
            self.send_notification('High Memory Usage', msg)
        
        if metrics.get('disk', 0) > thresholds['disk']:
            msg = f"High Disk Usage: {metrics['disk']:.1f}%"
            alerts.append(('disk', msg, 'critical'))
            self.send_notification('High Disk Usage', msg)
        
        if metrics.get('temp', 0) > thresholds['temperature']:
            msg = f"High Temperature: {metrics['temp']:.1f}°C"
            alerts.append(('temperature', msg, 'critical'))
            self.send_notification('High Temperature', msg)
        
        if 0 < metrics.get('battery', 100) < thresholds['battery']:
            msg = f"Low Battery: {metrics['battery']:.1f}%"
            alerts.append(('battery', msg, 'warning'))
            self.send_notification('Low Battery', msg)
        
        # Log alerts to database
        for alert_type, msg, severity in alerts:
            st.session_state.db.log_alert(alert_type, msg, severity)
        
        return alerts
    
    def send_notification(self, title, message):
        """Send desktop notification"""
        if NOTIFICATIONS_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name='System Monitor',
                    timeout=10
                )
            except:
                pass

# Initialize alert manager
if 'alert_manager' not in st.session_state:
    st.session_state.alert_manager = AlertManager()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_size(bytes_val):
    """Convert bytes into human-readable format"""
    if bytes_val >= 1024**4:
        return f"{bytes_val / (1024**4):.2f} TB"
    elif bytes_val >= 1024**3:
        return f"{bytes_val / (1024**3):.2f} GB"
    elif bytes_val >= 1024**2:
        return f"{bytes_val / (1024**2):.2f} MB"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.2f} KB"
    else:
        return f"{bytes_val} bytes"

def folder_size_bytes(folder_path: str):
    """Calculate total size of a folder"""
    total = 0
    try:
        for dirpath, _, filenames in os.walk(folder_path):
            for f in filenames:
                try:
                    fp = os.path.join(dirpath, f)
                    total += os.path.getsize(fp)
                except:
                    continue
    except:
        pass
    return total

def compute_folder_sizes(root_path, max_depth=2, min_size_bytes=10*1024*1024, progress_callback=None):
    """
    Recursively compute folder sizes up to max_depth.
    Returns a list of dicts with name, path, parent, and size.
    """
    results = []
    root_path = os.path.abspath(root_path)

    def _walk(path, depth, parent_name):
        total_size = 0
        try:
            for entry in os.scandir(path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total_size += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False) and depth < max_depth:
                        child_size = _walk(entry.path, depth+1, entry.name)
                        if child_size >= min_size_bytes:
                            results.append({
                                "name": entry.name,
                                "path": entry.path,
                                "parent": parent_name,
                                "size": child_size
                            })
                        total_size += child_size
                except Exception:
                    continue
        except Exception:
            pass
        if progress_callback:
            progress_callback(len(results))
        return total_size

    root_size = _walk(root_path, 0, os.path.basename(root_path))
    results.append({
        "name": os.path.basename(root_path),
        "path": root_path,
        "parent": "root",
        "size": root_size
    })
    return results


# ============================================================================
# ADDITIONAL HELPER FUNCTIONS FROM ORIGINAL SCRIPT  
# ============================================================================

def run_elevated_cmd(cmd: str):
    """Run command in elevated CMD window"""
    ps_cmd = f"Start-Process cmd -ArgumentList '/k {cmd}' -Verb RunAs"
    try:
        subprocess.run(["powershell", "-Command", ps_cmd], check=False)
        return True
    except Exception:
        return False

def run_elevated_exe(exe_path: str, args: str = ""):
    """Run executable with elevation"""
    safe_args = args.replace("'", "''") if args else ""
    if safe_args:
        ps_cmd = f"Start-Process -FilePath '{exe_path}' -ArgumentList '{safe_args}' -Verb RunAs"
    else:
        ps_cmd = f"Start-Process -FilePath '{exe_path}' -Verb RunAs"
    try:
        subprocess.run(["powershell", "-Command", ps_cmd], check=False)
        return True
    except Exception:
        return False

def run_cmd_capture(cmd_list):
    """Run command and capture output"""
    try:
        proc = subprocess.run(cmd_list, capture_output=True, text=True, shell=False)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return -1, "", str(e)

def get_public_ip_info():
    """Get public IP information"""
    try:
        with urllib.request.urlopen("https://ipinfo.io/json", timeout=6) as resp:
            data = json.load(resp)
            return {
                "ip": data.get("ip"),
                "org": data.get("org"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
            }
    except Exception:
        return None

def parse_dns_from_ipconfig():
    """Parse DNS servers from ipconfig"""
    try:
        rc, out, err = run_cmd_capture(["ipconfig", "/all"])
        if rc != 0:
            return []
        dns = []
        capture = False
        for line in out.splitlines():
            line = line.rstrip()
            if not line:
                capture = False
                continue
            if "DNS Servers" in line:
                parts = line.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    dns.append(parts[1].strip())
                capture = True
                continue
            if capture:
                if line.strip():
                    dns.append(line.strip())
                else:
                    capture = False
        return list(dict.fromkeys([d for d in dns if d]))
    except Exception:
        return []

def parse_ipconfig_adapters():
    """Parse network adapters from ipconfig"""
    rc, out, err = run_cmd_capture(["ipconfig", "/all"])
    adapters = []
    if rc != 0 or not out:
        return adapters
    lines = out.splitlines()
    current = None
    for raw in lines:
        line = raw.rstrip()
        if not line:
            continue
        if not line.startswith(" ") and line.endswith(":"):
            if current:
                adapters.append(current)
            current = {"name": line.strip().rstrip(":"), "ipv4": None, "default_gateway": None, "media_state": None}
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.lower().startswith("media state"):
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                current["media_state"] = parts[1].strip()
        if stripped.lower().startswith("ipv4 address") or stripped.lower().startswith("ip address"):
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                ip = parts[1].split("(")[0].strip()
                current["ipv4"] = ip
        if stripped.lower().startswith("default gateway"):
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                gw = parts[1].strip()
                if gw:
                    current["default_gateway"] = gw
    if current:
        adapters.append(current)
    return adapters

def is_internet_reachable(timeout=2):
    """Check if internet is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(("8.8.8.8", 53))
        sock.close()
        return True
    except Exception:
        return False

def run_elevated_powershell_and_read_json(ps_commands: str, timeout_seconds: int = 60):
    """Run PowerShell script elevated and read JSON output"""
    tmp_dir = tempfile.gettempdir()
    out_json = os.path.join(tmp_dir, f"st_ev_out_{int(time.time())}.json")
    ps1_path = os.path.join(tmp_dir, f"st_ev_cmd_{int(time.time())}.ps1")

    ps1_content = f"""
try {{
    $ErrorActionPreference = 'Stop'
    $result = & {{
        {ps_commands}
    }}
    $json = $result | ConvertTo-Json -Depth 6
    Set-Content -Path '{out_json}' -Value $json -Encoding UTF8
}} catch {{
    $errObj = @{{__error = $_.Exception.Message; __stack = $_.Exception.StackTrace}}
    $json = $errObj | ConvertTo-Json -Depth 6
    Set-Content -Path '{out_json}' -Value $json -Encoding UTF8
}}
"""
    try:
        with open(ps1_path, "w", encoding="utf-8") as f:
            f.write(ps1_content)
    except Exception as e:
        return False, f"Failed to write temporary PowerShell script: {e}"

    start_cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','{ps1_path}' -Verb RunAs -Wait"
    ]
    try:
        subprocess.run(start_cmd, check=False)
    except Exception as e:
        return False, f"Failed to start elevated PowerShell: {e}"

    waited = 0
    poll_interval = 0.5
    while waited < timeout_seconds:
        if os.path.exists(out_json):
            try:
                with open(out_json, "r", encoding="utf-8") as f:
                    content_json = f.read()
                try:
                    parsed = json.loads(content_json)
                    try:
                        os.remove(ps1_path)
                    except Exception:
                        pass
                    try:
                        os.remove(out_json)
                    except Exception:
                        pass
                    return True, parsed
                except Exception as e:
                    try:
                        os.remove(ps1_path)
                    except Exception:
                        pass
                    try:
                        os.remove(out_json)
                    except Exception:
                        pass
                    return False, f"Elevated command produced non-JSON output: {e}\n\nRaw output:\n{content_json}"
            except Exception as e:
                return False, f"Failed to read elevated output file: {e}"
        time.sleep(poll_interval)
        waited += poll_interval

    return False, "Timed out waiting for elevated command to produce output."

def parse_dotnet_date(value):
    """Parse .NET date format"""
    if pd.isna(value):
        return value
    if isinstance(value, (int, float)):
        try:
            return pd.to_datetime(int(value), unit='ms')
        except Exception:
            return value
    if isinstance(value, str):
        m = re.search(r"/Date\((\d+)\)/", value)
        if m:
            try:
                ms = int(m.group(1))
                return pd.to_datetime(ms, unit='ms')
            except Exception:
                return value
        try:
            return pd.to_datetime(value)
        except Exception:
            return value
    return value

def sanitize_key(s: str):
    """Sanitize string for use as key"""
    if s is None:
        return "none"
    return re.sub(r'[^0-9A-Za-z_]+', '_', str(s))

def format_time_for_export(value):
    """Format time for export"""
    if pd.isna(value):
        return ""
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    if isinstance(value, str):
        m = re.search(r"/Date\((\d+)\)/", value)
        if m:
            try:
                ms = int(m.group(1))
                return pd.to_datetime(ms, unit='ms').strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return value
        try:
            dt = pd.to_datetime(value)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return value
    if isinstance(value, (int, float)):
        try:
            return pd.to_datetime(int(value), unit='ms').strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(value)
    return str(value)

def safe_delete_folder_files(folder_path: str):
    """Safely delete files in a folder"""
    removed = 0
    skipped = 0
    if not os.path.exists(folder_path):
        return removed, skipped
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            path = os.path.join(root, f)
            try:
                os.remove(path)
                removed += 1
            except:
                skipped += 1
    return removed, skipped

# ============================================================================
# HARDWARE MONITORING FUNCTIONS
# ============================================================================

def get_cpu_temperature():
    """Get CPU temperature (Windows)"""
    temps = []
    try:
        # Try using psutil sensors (Linux)
        if hasattr(psutil, "sensors_temperatures"):
            temps_dict = psutil.sensors_temperatures()
            if temps_dict:
                for name, entries in temps_dict.items():
                    for entry in entries:
                        temps.append({
                            'name': entry.label or name,
                            'current': entry.current,
                            'high': entry.high,
                            'critical': entry.critical
                        })
    except:
        pass
    
    # Windows alternative - use WMI if available
    if WINDOWS and not temps:
        try:
            import wmi
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            temperature_infos = w.Sensor()
            for sensor in temperature_infos:
                if sensor.SensorType == 'Temperature' and 'CPU' in sensor.Name:
                    temps.append({
                        'name': sensor.Name,
                        'current': sensor.Value,
                        'high': sensor.Max,
                        'critical': None
                    })
        except:
            pass
    
    return temps if temps else None

def get_gpu_info():
    """Get GPU information and temperature"""
    gpu_info = []
    
    if GPU_AVAILABLE:
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                gpu_info.append({
                    'name': gpu.name,
                    'temp': gpu.temperature,
                    'load': gpu.load * 100,
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal,
                    'memory_percent': (gpu.memoryUsed / gpu.memoryTotal * 100) if gpu.memoryTotal > 0 else 0
                })
        except:
            pass
    
    return gpu_info if gpu_info else None

def get_battery_info():
    """Get comprehensive battery information"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            time_left = battery.secsleft / 3600 if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
            
            return {
                'percent': battery.percent,
                'power_plugged': battery.power_plugged,
                'time_left': time_left,
                'status': 'Charging' if battery.power_plugged else 'Discharging',
                'time_left_str': f"{time_left:.1f} hours" if time_left else "N/A"
            }
    except:
        pass
    return None

def generate_battery_report():
    """Generate Windows battery report"""
    if not WINDOWS:
        return None
    
    try:
        report_path = os.path.join(tempfile.gettempdir(), 'battery-report.html')
        subprocess.run(['powercfg', '/batteryreport', '/output', report_path], 
                      capture_output=True, shell=True, timeout=30)
        if os.path.exists(report_path):
            return report_path
    except:
        pass
    return None

# ============================================================================
# NETWORK MONITORING FUNCTIONS
# ============================================================================

def get_network_connections():
    """Get active network connections"""
    try:
        connections = psutil.net_connections(kind='inet')
        conn_list = []
        
        for conn in connections:
            try:
                if conn.pid:
                    try:
                        process = psutil.Process(conn.pid)
                        process_name = process.name()
                    except:
                        process_name = "Unknown"
                else:
                    process_name = "System"
                
                local_addr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
                remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
                
                conn_list.append({
                    'Process': process_name,
                    'PID': conn.pid if conn.pid else 0,
                    'Local Address': local_addr,
                    'Remote Address': remote_addr,
                    'Status': conn.status,
                    'Family': 'IPv4' if conn.family == socket.AF_INET else 'IPv6'
                })
            except:
                continue
        
        return pd.DataFrame(conn_list)
    except:
        return pd.DataFrame()

def get_network_stats():
    """Get network interface statistics"""
    try:
        stats = psutil.net_io_counters(pernic=True)
        net_stats = []
        
        for interface, stat in stats.items():
            net_stats.append({
                'Interface': interface,
                'Bytes Sent': format_size(stat.bytes_sent),
                'Bytes Received': format_size(stat.bytes_recv),
                'Packets Sent': stat.packets_sent,
                'Packets Received': stat.packets_recv,
                'Errors In': stat.errin,
                'Errors Out': stat.errout,
                'Drop In': stat.dropin,
                'Drop Out': stat.dropout
            })
        
        return pd.DataFrame(net_stats)
    except:
        return pd.DataFrame()

# ============================================================================
# BENCHMARK FUNCTIONS
# ============================================================================

def benchmark_cpu(iterations=5):
    """Simple CPU benchmark"""
    import timeit
    
    def cpu_task():
        result = 0
        for i in range(1000000):
            result += i ** 2
        return result
    
    try:
        time_taken = timeit.timeit(cpu_task, number=iterations)
        score = (iterations * 1000) / time_taken  # Higher is better
        
        return {
            'score': score,
            'time_seconds': time_taken,
            'iterations': iterations,
            'status': 'completed'
        }
    except Exception as e:
        return {
            'score': 0,
            'time_seconds': 0,
            'iterations': iterations,
            'status': f'failed: {e}'
        }

def benchmark_memory(size_mb=100):
    """Memory speed benchmark"""
    try:
        import numpy as np
        
        # Allocate array
        start = time.time()
        data = np.random.rand(size_mb * 1024 * 1024 // 8)  # 8 bytes per float64
        alloc_time = time.time() - start
        
        # Read test
        start = time.time()
        _ = data.sum()
        read_time = time.time() - start
        
        # Write test
        start = time.time()
        data[:] = 1.0
        write_time = time.time() - start
        
        del data
        
        read_speed = size_mb / read_time if read_time > 0 else 0
        write_speed = size_mb / write_time if write_time > 0 else 0
        
        return {
            'read_speed_mbps': read_speed,
            'write_speed_mbps': write_speed,
            'alloc_time': alloc_time,
            'status': 'completed'
        }
    except Exception as e:
        return {
            'read_speed_mbps': 0,
            'write_speed_mbps': 0,
            'alloc_time': 0,
            'status': f'failed: {e}'
        }

def benchmark_disk(test_size_mb=100):
    """Disk read/write speed benchmark"""
    try:
        # Write test
        data = os.urandom(test_size_mb * 1024 * 1024)
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        
        start = time.time()
        temp_file.write(data)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        write_time = time.time() - start
        temp_file.close()
        
        # Read test
        start = time.time()
        with open(temp_file.name, 'rb') as f:
            _ = f.read()
        read_time = time.time() - start
        
        os.unlink(temp_file.name)
        
        write_speed = test_size_mb / write_time if write_time > 0 else 0
        read_speed = test_size_mb / read_time if read_time > 0 else 0
        
        return {
            'write_speed_mbps': write_speed,
            'read_speed_mbps': read_speed,
            'status': 'completed'
        }
    except Exception as e:
        return {
            'write_speed_mbps': 0,
            'read_speed_mbps': 0,
            'status': f'failed: {e}'
        }

def benchmark_network():
    """Network speed test"""
    try:
        # Simple latency test to common DNS
        start = time.time()
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        latency = (time.time() - start) * 1000
        
        return {
            'latency_ms': latency,
            'status': 'completed'
        }
    except Exception as e:
        return {
            'latency_ms': 0,
            'status': f'failed: {e}'
        }

# ============================================================================
# SYSTEM INFORMATION FUNCTIONS
# ============================================================================

def get_detailed_system_info():
    """Get comprehensive system information"""
    info = {}
    
    # Operating System
    info['OS'] = platform.system()
    info['OS Version'] = platform.version()
    info['OS Release'] = platform.release()
    info['Architecture'] = platform.machine()
    info['Hostname'] = socket.gethostname()
    info['Processor'] = platform.processor()
    
    # CPU Info
    info['CPU Cores (Physical)'] = psutil.cpu_count(logical=False)
    info['CPU Cores (Logical)'] = psutil.cpu_count(logical=True)
    info['CPU Frequency'] = f"{psutil.cpu_freq().current:.2f} MHz" if psutil.cpu_freq() else "N/A"
    
    # Memory Info
    mem = psutil.virtual_memory()
    info['Total RAM'] = format_size(mem.total)
    info['Available RAM'] = format_size(mem.available)
    
    # Disk Info
    disk = psutil.disk_usage('/')
    info['Total Disk'] = format_size(disk.total)
    info['Free Disk'] = format_size(disk.free)
    
    # Boot Time
    info['Boot Time'] = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    
    # Python Info
    info['Python Version'] = platform.python_version()
    
    return info

def get_windows_services():
    """Get Windows services information"""
    if not WINDOWS:
        return pd.DataFrame()
    
    try:
        import wmi
        c = wmi.WMI()
        services = []
        
        for service in c.Win32_Service():
            services.append({
                'Name': service.Name,
                'Display Name': service.DisplayName,
                'State': service.State,
                'Start Mode': service.StartMode,
                'Status': service.Status,
                'Path': service.PathName
            })
        
        return pd.DataFrame(services)
    except:
        return pd.DataFrame()

# ============================================================================
# PROCESS MONITORING FUNCTIONS (from original script)
# ============================================================================

def get_recent_files(root_path, days=1, mode="modified", max_depth=3, limit=200):
    """Get recently modified/created files"""
    cutoff = time.time() - days*86400
    records = []
    root_depth = root_path.count(os.sep)
    
    try:
        for dirpath, _, filenames in os.walk(root_path):
            if dirpath.count(os.sep) - root_depth >= max_depth:
                continue
            for f in filenames:
                try:
                    fp = os.path.join(dirpath, f)
                    stat = os.stat(fp)
                    ts = stat.st_mtime if mode == "modified" else stat.st_ctime
                    if ts >= cutoff:
                        records.append({
                            "File": fp,
                            "Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                            "Size": format_size(stat.st_size)
                        })
                        if len(records) >= limit:
                            return pd.DataFrame(records)
                except:
                    continue
    except:
        pass
    
    return pd.DataFrame(records)

def get_recent_installed_programs(days=1):
    """Get recently installed programs"""
    if not WINDOWS:
        return pd.DataFrame()
    
    cutoff = time.time() - days*86400
    records = []
    uninstall_keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    
    try:
        for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for key_path in uninstall_keys:
                try:
                    with winreg.OpenKey(root, key_path) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                    install_date, _ = winreg.QueryValueEx(subkey, "InstallDate")
                                    if install_date:
                                        try:
                                            dt = time.strptime(str(install_date), "%Y%m%d")
                                            ts = time.mktime(dt)
                                            if ts >= cutoff:
                                                records.append({
                                                    "Program": name,
                                                    "InstallDate": time.strftime("%Y-%m-%d", dt)
                                                })
                                        except:
                                            continue
                            except:
                                continue
                except:
                    continue
    except:
        pass
    
    return pd.DataFrame(records)

# ============================================================================
# STREAMLIT APP CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Enhanced System Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🖥️"
)

# Dynamic theme CSS — applied based on sidebar selection
_theme = st.session_state.get("app_theme", "Light")

_dark_css = """
    /* ── DARK THEME ── */
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], .main, .block-container {
        background-color: #0e1117 !important;
        color: #fafafa !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background-color: #1a1d27 !important;
        color: #fafafa !important;
    }
    /* headers, labels, captions */
    h1, h2, h3, h4, h5, h6,
    .stMarkdown, label, p,
    [data-testid="stCaptionContainer"],
    [data-testid="stMetricLabel"] > div,
    [data-testid="stMetricValue"] > div,
    [data-testid="stMetricDelta"] > div {
        color: #fafafa !important;
    }
    /* text inputs, selects */
    input, textarea, select,
    [data-baseweb="input"] input,
    [data-baseweb="select"] div {
        background-color: #262730 !important;
        color: #fafafa !important;
        border-color: #444 !important;
    }
    /* dataframe / table */
    [data-testid="stDataFrame"] table,
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] td {
        background-color: #1e2130 !important;
        color: #fafafa !important;
    }
    /* metric cards */
    [data-testid="stMetric"] {
        background-color: #1e2130 !important;
        border-radius: 8px;
        padding: 8px;
    }
    /* divider */
    hr { border-color: #333 !important; }
    /* tabs */
    button[data-baseweb="tab"] {
        background-color: #1a1d27 !important;
        color: #ccc !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #fff !important;
        border-bottom: 2px solid #6c8cff !important;
    }
    /* expander */
    [data-testid="stExpander"] {
        background-color: #1e2130 !important;
        border-color: #333 !important;
    }
    /* expander header text */
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {
        color: #fafafa !important;
    }
    /* info / warning / success / error boxes */
    [data-testid="stAlert"] {
        background-color: #1e2130 !important;
    }
    /* ── BUTTONS (all variants) ── */
    /* Secondary / default button */
    [data-testid="stButton"] > button,
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondary"] > button,
    button[kind="secondary"],
    .stButton > button {
        background-color: #2d3147 !important;
        color: #e8eaf6 !important;
        border: 1px solid #555a82 !important;
    }
    [data-testid="stButton"] > button:hover,
    [data-testid="stBaseButton-secondary"]:hover,
    .stButton > button:hover {
        background-color: #3a3f5c !important;
        color: #ffffff !important;
        border-color: #7986cb !important;
    }
    /* Primary button */
    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-primary"] > button,
    button[kind="primary"],
    .stButton > button[kind="primary"] {
        background-color: #3d52b8 !important;
        color: #ffffff !important;
        border: 1px solid #5c6bc0 !important;
    }
    [data-testid="stBaseButton-primary"]:hover,
    button[kind="primary"]:hover {
        background-color: #4d62c8 !important;
        color: #ffffff !important;
    }
    /* Download button */
    [data-testid="stDownloadButton"] > button,
    [data-testid="stBaseButton-secondary"][data-testid="stDownloadButton"] {
        background-color: #1b3a2d !important;
        color: #a5d6a7 !important;
        border: 1px solid #388e3c !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        background-color: #1e4d3a !important;
        color: #c8e6c9 !important;
    }
    /* Make sure button text is never invisible */
    button p, button span, button div {
        color: inherit !important;
    }
    /* Checkbox, radio, multiselect labels */
    [data-testid="stCheckbox"] label,
    [data-testid="stRadio"] label,
    [data-testid="stMultiSelect"] label,
    [data-testid="stSelectbox"] label,
    [data-testid="stSlider"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stTextInput"] label {
        color: #fafafa !important;
    }
    /* Multiselect tags */
    [data-baseweb="tag"] {
        background-color: #3d4166 !important;
        color: #fafafa !important;
    }
    /* Selectbox / dropdown options panel */
    [data-baseweb="popover"] ul,
    [data-baseweb="menu"] ul {
        background-color: #1e2130 !important;
    }
    [data-baseweb="menu"] li,
    [data-baseweb="popover"] li {
        color: #fafafa !important;
    }
    [data-baseweb="menu"] li:hover,
    [data-baseweb="popover"] li:hover {
        background-color: #2d3147 !important;
    }
    /* Number input arrows */
    [data-testid="stNumberInput"] button {
        background-color: #2d3147 !important;
        color: #fafafa !important;
        border-color: #444 !important;
    }
    /* Slider track */
    [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
        background-color: #6c8cff !important;
    }
"""

_light_css = """
    /* ── LIGHT THEME ── */
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], .main, .block-container {
        background-color: #ffffff !important;
        color: #262730 !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background-color: #f0f2f6 !important;
        color: #262730 !important;
    }
    [data-testid="stMetric"] {
        background-color: #f0f2f6 !important;
        border-radius: 8px;
        padding: 8px;
    }
"""

_auto_css = """
    /* ── AUTO THEME — honour OS preference ── */
    @media (prefers-color-scheme: dark) {
        html, body, [data-testid="stAppViewContainer"],
        [data-testid="stMain"], .main, .block-container {
            background-color: #0e1117 !important;
            color: #fafafa !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background-color: #1a1d27 !important;
            color: #fafafa !important;
        }
        h1,h2,h3,h4,h5,h6,.stMarkdown,label,p,
        [data-testid="stCaptionContainer"],
        [data-testid="stMetricLabel"] > div,
        [data-testid="stMetricValue"] > div,
        [data-testid="stMetricDelta"] > div { color: #fafafa !important; }
        [data-testid="stMetric"] {
            background-color: #1e2130 !important;
            border-radius: 8px; padding: 8px;
        }
        hr { border-color: #333 !important; }
    }
    @media (prefers-color-scheme: light) {
        [data-testid="stMetric"] {
            background-color: #f0f2f6 !important;
            border-radius: 8px; padding: 8px;
        }
    }
"""

_theme_css_map = {"Light": _light_css, "Dark": _dark_css, "Auto": _auto_css}
_chosen_css = _theme_css_map.get(_theme, _light_css)

st.markdown(f"""
<style>
    /* ── BASE (always applied) ── */
    .metric-card {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    div[data-testid="stMetricValue"] {{
        font-size: 28px;
    }}
    /* ── SELECTED THEME ── */
    {_chosen_css}
</style>
""", unsafe_allow_html=True)

st.title("🖥️ Enhanced Real-Time System Monitor")
st.caption("Professional-grade system monitoring with hardware sensors, alerts, and analytics")

# Hard browser refresh button — clears all cached data and reruns the app
if st.button("🔄 Hard browser refresh (clears cached files)", key="btn_hard_refresh"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

with st.sidebar:
    st.header("⚙️ Settings")
    
    # Manual refresh only
    if st.button("🔄 Refresh Now", use_container_width=True, key="btn_manual_refresh"):
        st.rerun()
    
    st.info("💡 Tip: Click 'Refresh Now' to update gauges and metrics")
    
    st.divider()
    
    # Theme selection
    theme = st.selectbox("🎨 Theme", ["Light", "Dark", "Auto"],
                         index=["Light", "Dark", "Auto"].index(
                             st.session_state.get("app_theme", "Light")))
    st.session_state["app_theme"] = theme
    
    # Data logging
    st.subheader("📊 Data Logging")
    enable_logging = st.checkbox("Enable metrics logging", value=True)
    log_interval = st.slider("Log interval (minutes)", 1, 60, 5)
    
    st.divider()
    
    # Alerts configuration
    st.subheader("🔔 Alert Settings")
    alerts_enabled = st.checkbox("Enable alerts", value=True)
    st.session_state.alerts_enabled = alerts_enabled
    
    if alerts_enabled:
        st.session_state.alert_thresholds['cpu'] = st.slider("CPU threshold (%)", 0, 100, 80)
        st.session_state.alert_thresholds['memory'] = st.slider("Memory threshold (%)", 0, 100, 85)
        st.session_state.alert_thresholds['disk'] = st.slider("Disk threshold (%)", 0, 100, 90)
        st.session_state.alert_thresholds['temperature'] = st.slider("Temperature threshold (°C)", 0, 100, 80)
        st.session_state.alert_thresholds['battery'] = st.slider("Battery threshold (%)", 0, 100, 20)


# ============================================================================
# COLLECT CURRENT METRICS
# ============================================================================

@st.cache_data(ttl=2)
def get_current_metrics():
    """Get current system metrics (cached for 2 seconds)"""
    metrics = {}
    
    # CPU
    metrics['cpu'] = psutil.cpu_percent(interval=1)
    metrics['cpu_per_core'] = psutil.cpu_percent(interval=1, percpu=True)
    
    # Memory
    mem = psutil.virtual_memory()
    metrics['memory'] = mem.percent
    metrics['memory_used'] = mem.used
    metrics['memory_total'] = mem.total
    metrics['memory_available'] = mem.available
    
    # Disk
    disk = psutil.disk_usage('/')
    metrics['disk'] = disk.percent
    metrics['disk_used'] = disk.used
    metrics['disk_total'] = disk.total
    metrics['disk_free'] = disk.free
    
    # Network
    net = psutil.net_io_counters()
    metrics['net_sent'] = net.bytes_sent
    metrics['net_recv'] = net.bytes_recv
    
    # Temperature
    cpu_temps = get_cpu_temperature()
    if cpu_temps:
        metrics['temp'] = cpu_temps[0]['current']
    else:
        metrics['temp'] = 0
    
    # Battery
    battery = get_battery_info()
    if battery:
        metrics['battery'] = battery['percent']
    else:
        metrics['battery'] = 100
    
    # GPU
    gpu_info = get_gpu_info()
    if gpu_info:
        metrics['gpu_temp'] = gpu_info[0]['temp']
        metrics['gpu_load'] = gpu_info[0]['load']
    
    return metrics

# Get current metrics
current_metrics = get_current_metrics()

# Check alerts
alerts = st.session_state.alert_manager.check_thresholds(current_metrics)

# Log metrics to database
if enable_logging:
    st.session_state.db.log_metrics(current_metrics)

# Display active alerts
if alerts:
    for alert_type, msg, severity in alerts:
        if severity == 'critical':
            st.error(f"🚨 {msg}")
        else:
            st.warning(f"⚠️ {msg}")

# ============================================================================
# TAB NAVIGATION
# ============================================================================

# ============================================================================
# TAB NAVIGATION - BACK AT THE TOP
# ============================================================================

# ============================================================================
# OVERVIEW CONTENT FUNCTION  (defined here so st.fragment can call it)
# ============================================================================

def _draw_overview():
    """Render all Overview tab content — called from fragment for live refresh."""
    m = get_current_metrics()   # always fetch fresh inside the fragment

    # ── Metric cards ──────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("CPU Usage",    f"{m['cpu']:.1f}%",
                  delta=None, help="Current CPU utilization")
    with col2:
        st.metric("Memory Usage", f"{m['memory']:.1f}%",
                  delta=f"{format_size(m['memory_used'])} / {format_size(m['memory_total'])}",
                  help="RAM usage")
    with col3:
        st.metric("Disk Usage",   f"{m['disk']:.1f}%",
                  delta=f"{format_size(m['disk_free'])} free",
                  help="Disk space usage")
    with col4:
        if m.get('temp', 0) > 0:
            st.metric("CPU Temperature", f"{m['temp']:.1f}°C", help="CPU temperature")
        else:
            batt = get_battery_info()
            if batt:
                st.metric("Battery", f"{batt['percent']:.0f}%",
                          delta=batt['status'], help="Battery status")
            else:
                st.metric("System", "Running", help="System status")

    st.divider()

    # ── Animated SVG gauges ───────────────────────────────────────────────────
    def _gc(pct):       # arc colour
        return "#4caf50" if pct < 50 else "#ff9800" if pct < 80 else "#f44336"
    def _gb(pct):       # track colour
        return "#1b3a1f" if pct < 50 else "#3a2800" if pct < 80 else "#3a0f0f"
    def _gauge(label, value, anim_id):
        r    = 80
        full = 3.14159 * r
        gap  = full * (1 - value / 100)
        c, bg = _gc(value), _gb(value)
        return f"""
<div style="text-align:center; padding:0 8px;">
  <svg viewBox="0 0 200 120" width="100%"
       style="max-width:260px; display:block; margin:0 auto;">
    <defs><style>
      @keyframes sweep-{anim_id} {{
        from {{ stroke-dashoffset: {full:.1f}; }}
        to   {{ stroke-dashoffset: {gap:.1f}; }}
      }}
    </style></defs>
    <path d="M 20 100 A {r} {r} 0 0 1 180 100"
          fill="none" stroke="{bg}" stroke-width="18" stroke-linecap="round"/>
    <path d="M 20 100 A {r} {r} 0 0 1 180 100"
          fill="none" stroke="{c}" stroke-width="18" stroke-linecap="round"
          stroke-dasharray="{full:.1f}" stroke-dashoffset="{gap:.1f}"
          style="animation: sweep-{anim_id} 1.2s cubic-bezier(0.4,0,0.2,1) both;"/>
    <text x="100" y="88" text-anchor="middle" font-size="26" font-weight="700"
          font-family="sans-serif" fill="{c}">{value}%</text>
    <text x="100" y="112" text-anchor="middle" font-size="12"
          font-family="sans-serif" fill="#aaa">{label}</text>
  </svg>
</div>"""

    gc1, gc2, gc3 = st.columns(3)
    cpu_v  = round(m['cpu'], 1)
    mem_v  = round(m['memory'], 1)
    disk_v = round(m['disk'], 1)
    with gc1:
        st.markdown(_gauge("CPU Usage",    cpu_v,  "cpu"),  unsafe_allow_html=True)
    with gc2:
        st.markdown(_gauge("Memory Usage", mem_v,  "mem"),  unsafe_allow_html=True)
    with gc3:
        st.markdown(_gauge("Disk Usage",   disk_v, "disk"), unsafe_allow_html=True)

    st.divider()

    # ── Quick Stats ───────────────────────────────────────────────────────────
    st.subheader("Quick Stats")
    qs1, qs2, qs3 = st.columns(3)
    with qs1:
        st.write("**Network**")
        st.write(f"📤 Sent: {format_size(m['net_sent'])}")
        st.write(f"📥 Received: {format_size(m['net_recv'])}")
    with qs2:
        st.write("**System**")
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime    = datetime.now() - boot_time
        st.write(f"⏱️ Uptime: {uptime.days}d {uptime.seconds//3600}h")
        st.write(f"💻 Processes: {len(psutil.pids())}")
    with qs3:
        st.write("**Performance**")
        if m.get('temp', 0) > 0:
            st.write(f"🌡️ Temperature: {m['temp']:.1f}°C")
        if m.get('gpu_load'):
            st.write(f"🎮 GPU Load: {m['gpu_load']:.1f}%")


# JavaScript to persist active tab across reruns
st.markdown("""
<script>
(function() {
    function getTabButtons() {
        return Array.from(document.querySelectorAll('button[data-baseweb="tab"]'));
    }

    function saveActiveTab() {
        var buttons = getTabButtons();
        buttons.forEach(function(btn, idx) {
            btn.addEventListener('click', function() {
                sessionStorage.setItem('activeTabIndex', idx);
            });
        });
    }

    function restoreActiveTab() {
        var savedIdx = sessionStorage.getItem('activeTabIndex');
        if (savedIdx === null) return;
        var idx = parseInt(savedIdx);
        var tryRestore = setInterval(function() {
            var buttons = getTabButtons();
            if (buttons.length > idx) {
                clearInterval(tryRestore);
                saveActiveTab();
                if (buttons[idx] && !buttons[idx].getAttribute('aria-selected') !== 'true') {
                    buttons[idx].click();
                }
            }
        }, 150);
        setTimeout(function() { clearInterval(tryRestore); }, 5000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            restoreActiveTab();
            saveActiveTab();
        });
    } else {
        restoreActiveTab();
        saveActiveTab();
    }

    var observer = new MutationObserver(function() {
        var buttons = getTabButtons();
        if (buttons.length > 0) {
            saveActiveTab();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "📊 Overview",
    "⚡ Processes", 
    "📈 Performance Charts",
    "🚀 Startup Apps",
    "🔧 Advanced Tools",
    "🌐 Network Tools",
    "📝 Event Viewer",
    "📂 Recent Activity",
    "🌡️ Hardware Monitor",
    "🔋 Battery & Power",
    "🔔 Alerts & Logs",
    "🏃 Benchmarks",
    "💻 System Info",
    "🔌 Network Connections",
    "⚙️ Services & Tasks"
])

# ============================================================================
# TAB 1: OVERVIEW
# ============================================================================

with tabs[0]:
    st.header("System Overview")

    # ── Real-time auto-refresh ─────────────────────────────────────────────────
    # st.fragment(run_every=3) re-runs ONLY this section every 3 seconds.
    # It lives inside tabs[0], so it only ticks while the Overview tab is shown.
    # Switching to another tab stops the refresh automatically.
    if hasattr(st, 'fragment'):
        @st.fragment(run_every=3)
        def _overview_fragment():
            _draw_overview()
        _overview_fragment()
    else:
        # Older Streamlit — static render, no auto-refresh
        _draw_overview()

# ============================================================================
# TAB 2: PROCESSES
# ============================================================================

with tabs[1]:
    st.header("Process Manager")
    
    # Get process list
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username']):
        try:
            pinfo = proc.info
            processes.append({
                'PID': pinfo['pid'],
                'Name': pinfo['name'],
                'CPU %': pinfo['cpu_percent'],
                'Memory %': pinfo['memory_percent'],
                'Status': pinfo['status'],
                'User': pinfo['username']
            })
        except:
            continue
    
    df_processes = pd.DataFrame(processes)
    
    # Filters
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        sort_by = st.selectbox("Sort by", ['CPU %', 'Memory %', 'PID', 'Name'])
    
    with filter_col2:
        filter_name = st.text_input("Filter by name", "")
    
    # Apply filters
    if filter_name:
        df_processes = df_processes[df_processes['Name'].str.contains(filter_name, case=False, na=False)]
    
    df_processes = df_processes.sort_values(by=sort_by, ascending=False)
    
    # Display
    st.dataframe(df_processes, use_container_width=True, height=500)
    
    st.caption(f"Total processes: {len(processes)}")
    
    # Kill process option
    with st.expander("⚠️ Kill Process (Advanced)"):
        pid_to_kill = st.number_input("Enter PID to kill", min_value=1, step=1)
        if st.button("Kill Process", type="primary", key="btn_2"):
            try:
                proc = psutil.Process(pid_to_kill)
                proc.terminate()
                st.success(f"Process {pid_to_kill} terminated. Refresh the process list to see updated results.")
            except Exception as e:
                st.error(f"Error: {e}")

# ============================================================================
# TAB 3: PERFORMANCE CHARTS
# ============================================================================

with tabs[2]:
    st.header("Performance Charts")
    
    # Get historical data
    hist_data = st.session_state.db.get_historical_data(hours=24)
    
    if not hist_data.empty and PLOTLY_AVAILABLE:
        hist_data['timestamp'] = pd.to_datetime(hist_data['timestamp'])
        
        # CPU Chart
        st.subheader("CPU Usage (24 hours)")
        fig_cpu = px.line(hist_data, x='timestamp', y='cpu_percent', 
                         title='CPU Usage Over Time',
                         labels={'cpu_percent': 'CPU %', 'timestamp': 'Time'})
        fig_cpu.add_hline(y=st.session_state.alert_thresholds['cpu'], 
                         line_dash="dash", line_color="red",
                         annotation_text="Alert Threshold")
        st.plotly_chart(fig_cpu, use_container_width=True)
        
        # Memory Chart
        st.subheader("Memory Usage (24 hours)")
        fig_mem = px.line(hist_data, x='timestamp', y='memory_percent',
                         title='Memory Usage Over Time',
                         labels={'memory_percent': 'Memory %', 'timestamp': 'Time'})
        fig_mem.add_hline(y=st.session_state.alert_thresholds['memory'],
                         line_dash="dash", line_color="red",
                         annotation_text="Alert Threshold")
        st.plotly_chart(fig_mem, use_container_width=True)
        
        # Multi-metric chart
        st.subheader("Combined Metrics")
        fig_combined = go.Figure()
        fig_combined.add_trace(go.Scatter(x=hist_data['timestamp'], y=hist_data['cpu_percent'],
                                         mode='lines', name='CPU %'))
        fig_combined.add_trace(go.Scatter(x=hist_data['timestamp'], y=hist_data['memory_percent'],
                                         mode='lines', name='Memory %'))
        fig_combined.add_trace(go.Scatter(x=hist_data['timestamp'], y=hist_data['disk_percent'],
                                         mode='lines', name='Disk %'))
        fig_combined.update_layout(title='System Metrics Over Time',
                                  xaxis_title='Time',
                                  yaxis_title='Percentage (%)')
        st.plotly_chart(fig_combined, use_container_width=True)
        
        # Export option
        csv = hist_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Historical Data (CSV)",
            data=csv,
            file_name=f'system_metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv'
        )
    else:
        st.info("📊 Historical data will appear here once logging is enabled and data is collected.")
        st.write("Enable 'Data Logging' in the sidebar and wait a few minutes for data to accumulate.")

# ============================================================================
# TAB 4: STARTUP APPS (Placeholder from original)
# ============================================================================

with tabs[3]:
    st.header("Startup Applications")
    st.info("This feature shows applications configured to start with Windows.")
    
    if WINDOWS:
        startup_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ]
        
        startup_apps = []
        
        for hkey, path in startup_paths:
            try:
                with winreg.OpenKey(hkey, path) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            location = "User" if hkey == winreg.HKEY_CURRENT_USER else "System"
                            startup_apps.append({
                                'Name': name,
                                'Command': value,
                                'Location': location
                            })
                            i += 1
                        except OSError:
                            break
            except:
                continue
        
        if startup_apps:
            df_startup = pd.DataFrame(startup_apps)
            st.dataframe(df_startup, use_container_width=True)
        else:
            st.write("No startup applications found.")
        
        st.markdown("---")
        st.write("To enable/disable startup apps you can open the Windows Startup Apps settings (reliable) or open Task Manager (Startup tab).")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Open Startup Apps (Settings)", key="btn_startup_settings"):
                try:
                    if platform.system() == "Windows":
                        os.startfile("ms-settings:startupapps")
                        st.success("Opened Startup Apps settings.")
                except Exception:
                    st.warning("Could not open Startup Apps settings.")
        
        with col2:
            if st.button("Open Task Manager (Startup tab)", key="btn_startup_taskmgr"):
                try:
                    subprocess.Popen(["taskmgr"], shell=False)
                    st.success("Task Manager opened.")
                except Exception:
                    st.warning("Could not open Task Manager.")
    else:
        st.warning("Startup apps feature is only available on Windows.")

# ============================================================================
# TAB 5: ADVANCED TOOLS (COMPLETE VERSION - ALL FEATURES RESTORED)
# ============================================================================

with tabs[4]:
    st.header("Advanced Performance Metrics & Cleanup Tools")
    
    # TEMP FOLDER CLEANUP
    st.subheader("Temporary Files")
    temp_dir = tempfile.gettempdir()
    temp_size = folder_size_bytes(temp_dir)
    st.metric("Temp Folder Size", format_size(temp_size))
    
    if st.button("🧹 Clear Temp Files", key="btn_clear_temp"):
        removed, skipped = safe_delete_folder_files(temp_dir)
        if skipped > 0:
            st.warning(f"Cleared {removed} temp files. Skipped {skipped} files (close apps for full cleanup).")
        else:
            st.success(f"Cleared {removed} temp files.")
    
    # CHROME CACHE CLEANUP
    st.divider()
    st.subheader("Chrome Cache")
    chrome_cache = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Cache")
    
    if os.path.exists(chrome_cache):
        chrome_size = folder_size_bytes(chrome_cache)
        st.metric("Chrome Cache Size", format_size(chrome_size))
        
        if st.button("🧹 Clear Chrome Cache", key="btn_clear_chrome"):
            removed, skipped = safe_delete_folder_files(chrome_cache)
            if skipped > 0:
                st.warning(f"Cleared {removed} cache files. Skipped {skipped} files (close Chrome for full cleanup).")
            else:
                st.success(f"Cleared {removed} cache files.")
    else:
        st.info("Chrome cache not found.")
    
    # TEAMS CACHE CLEANUP
    st.divider()
    st.subheader("Microsoft Teams Cache")
    teams_cache = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Teams\Cache")
    teams_chat_cache = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Teams\IndexedDB")
    teams_local_storage = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Teams\Local Storage")
    
    teams_cache_exists = os.path.exists(teams_cache)
    teams_chat_exists = os.path.exists(teams_chat_cache) or os.path.exists(teams_local_storage)
    
    if not teams_cache_exists and not teams_chat_exists:
        st.info("Teams cache not found.")
    else:
        if teams_cache_exists:
            teams_size = folder_size_bytes(teams_cache)
            st.metric("Teams Cache Size", format_size(teams_size))
            if st.button("🧹 Clear Teams Cache", key="btn_clear_teams"):
                removed, skipped = safe_delete_folder_files(teams_cache)
                if skipped > 0:
                    st.warning(f"Cleared {removed} Teams cache files. Skipped {skipped} files.")
                else:
                    st.success(f"Cleared {removed} Teams cache files.")
        
        if teams_chat_exists:
            chat_size = folder_size_bytes(teams_chat_cache) + folder_size_bytes(teams_local_storage)
            st.metric("Teams Chat Cache Size", format_size(chat_size))
            if st.button("🧹 Clear Teams Chat Cache", key="btn_clear_teams_chat"):
                removed_total = 0
                skipped_total = 0
                for folder in [teams_chat_cache, teams_local_storage]:
                    r, s = safe_delete_folder_files(folder)
                    removed_total += r
                    skipped_total += s
                if skipped_total > 0:
                    st.warning(f"Cleared {removed_total} files. Skipped {skipped_total} files.")
                else:
                    st.success(f"Cleared {removed_total} files.")
    
    # CLEAR ALL CACHES
    if st.button("🧼 Clear All Caches (Temp, Chrome, Teams)", key="btn_clear_all"):
        total_removed = 0
        total_skipped = 0
        for folder in [temp_dir, chrome_cache, teams_cache, teams_chat_cache, teams_local_storage]:
            r, s = safe_delete_folder_files(folder) if os.path.exists(folder) else (0, 0)
            total_removed += r
            total_skipped += s
        if total_skipped > 0:
            st.warning(f"Cleared {total_removed} files. Skipped {total_skipped} files.")
        else:
            st.success(f"Cleared {total_removed} files.")
    
    # STORAGE ANALYZER (PYTHON-BASED)
    st.markdown("---")
    st.subheader("Storage Analyzer (Python-based)")
    
    analyze_clicked = st.button("Analyze Folder Sizes", key="btn_analyze_folder_sizes")
    
    if analyze_clicked:
        st.info("Analyzing C:\\ folder sizes (this may take 30-60 seconds)...")
        progress_placeholder = st.empty()
        
        def progress_callback(count):
            progress_placeholder.text(f"Scanned {count} folders...")
        
        results = compute_folder_sizes("C:\\", max_depth=2, min_size_bytes=10*1024*1024, progress_callback=progress_callback)
        
        if results:
            progress_placeholder.empty()
            st.success(f"Analysis complete! Found {len(results)} large folders.")
            
            df_folders = pd.DataFrame(results)
            df_folders["size_gb"] = df_folders["size"] / (1024**3)
            df_folders = df_folders.sort_values(by="size", ascending=False)
            
            st.dataframe(
                df_folders[["name", "size_gb", "parent"]].rename(columns={
                    "name": "Folder",
                    "size_gb": "Size (GB)",
                    "parent": "Parent"
                }),
                use_container_width=True,
                height=400
            )
            
            if PLOTLY_AVAILABLE:
                st.subheader("Visual Breakdown")
                fig = px.treemap(
                    df_folders,
                    path=["parent", "name"],
                    values="size",
                    title="Folder Size Treemap"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No large folders found or analysis failed.")
    
    # DISK VOLUMES
    st.markdown("---")
    st.subheader("Disk Volumes")
    if platform.system() == "Windows":
        try:
            ps_cmd = "Get-Volume | Select-Object DriveLetter, FileSystemLabel, FileSystem, @{Name='SizeGB';Expression={[math]::Round($_.Size/1GB,2)}}, @{Name='HealthStatus';Expression={$_.HealthStatus}} | ConvertTo-Json"
            result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                try:
                    parsed = json.loads(result.stdout)
                    if isinstance(parsed, dict):
                        parsed = [parsed]
                    vol_df = pd.DataFrame(parsed)
                    if not vol_df.empty:
                        vol_df = vol_df.rename(columns={
                            "DriveLetter": "Drive",
                            "FileSystemLabel": "Label",
                            "FileSystem": "FS",
                            "SizeGB": "Size (GB)",
                            "HealthStatus": "Health"
                        })
                        st.dataframe(vol_df[["Drive", "Label", "FS", "Size (GB)", "Health"]], use_container_width=True, height=300)
                    else:
                        st.info("No volumes found.")
                except Exception:
                    st.info("Could not parse volume information.")
        except Exception as e:
            st.warning(f"Could not retrieve volumes: {e}")
    
    # DISK FRAGMENTATION
    st.markdown("---")
    st.subheader("Disk Fragmentation Analysis (C:)")
    if platform.system() == "Windows":
        if st.button("Analyze C: (elevated) — UAC prompt", key="btn_analyze_defrag_elev"):
            st.info("Opening elevated command window for defrag analyze.")
            started = run_elevated_cmd("defrag C: /A")
            if started:
                st.success("Elevated defrag analyze started.")
            else:
                st.error("Failed to start elevated defrag.")
        
        if st.button("Optimize C: (defrag /O) — Elevated", key="btn_defrag_optimize"):
            st.info("Running optimization (may take time). UAC prompt will appear.")
            started = run_elevated_cmd("defrag C: /O")
            if started:
                st.success("Defrag optimize started in elevated window.")
            else:
                st.error("Failed to start defrag.")
        
        if st.button("Open Defragmentation GUI (dfrgui)", key="btn_defrag_gui"):
            st.info("Opening Defragmentation GUI with elevation.")
            started = run_elevated_exe("dfrgui.exe")
            if started:
                st.success("Defragmentation GUI started.")
            else:
                st.error("Could not open GUI.")
    
    # SYSTEM INTEGRITY & CLEANUP TOOLS
    st.markdown("---")
    st.subheader("System Integrity & Cleanup Tools (Admin Required)")
    
    if st.button("Run chkdsk C: (Open elevated CMD)", key="btn_chkdsk"):
        st.info("UAC prompt will appear. Command window will remain open.")
        run_elevated_cmd("chkdsk C:")
    
    if st.button("Run sfc /scannow (elevated)", key="btn_sfc"):
        st.info("Running System File Checker. Requires admin privileges.")
        run_elevated_cmd("sfc /scannow")
    
    if st.button("Analyze Component Store (DISM) — Elevated", key="btn_dism_analyze"):
        st.info("DISM analyze requires admin rights. UAC prompt will appear.")
        started = run_elevated_cmd("dism /Online /Cleanup-Image /AnalyzeComponentStore")
        if started:
            st.success("DISM analyze started in elevated window.")
        else:
            st.error("Failed to start DISM analyze.")
    
    if st.button("Run DISM StartComponentCleanup (elevated)", key="btn_dism_cleanup"):
        st.info("Running DISM StartComponentCleanup elevated.")
        run_elevated_cmd("dism /Online /Cleanup-Image /StartComponentCleanup")
    
    if st.button("Windows Update Cleanup (Disk Cleanup)", key="btn_disk_cleanup"):
        st.info("Opening Disk Cleanup (may require admin).")
        run_elevated_cmd("cleanmgr /sagerun:1")
    
    # UPTIME AND BATTERY
    st.markdown("---")
    uptime_seconds = time.time() - psutil.boot_time()
    uptime_hours = int(uptime_seconds // 3600)
    uptime_color = "🔴" if uptime_hours > 200 else "🟡" if uptime_hours > 100 else "🟢"
    st.metric("System Uptime", f"{uptime_color} {uptime_hours} hours")
    
    if hasattr(psutil, "sensors_battery"):
        battery = psutil.sensors_battery()
        if battery:
            batt_color = "🔴" if battery.percent < 20 else "🟡" if battery.percent < 50 else "🟢"
            st.metric("Battery", f"{batt_color} {battery.percent}% {'Charging' if battery.power_plugged else 'Discharging'}")

# ============================================================================
# TAB 6: NETWORK TOOLS (COMPLETE VERSION - ALL FEATURES RESTORED)
# ============================================================================

with tabs[5]:
    st.header("Network Tools & Diagnostics")
    
    # PUBLIC IP
    st.subheader("Public IP & ISP")
    ip_info = get_public_ip_info()
    if ip_info:
        st.write(f"**Public IP:** {ip_info.get('ip')}")
        st.write(f"**ISP / Org:** {ip_info.get('org')}")
        st.write(f"**Location:** {ip_info.get('city')}, {ip_info.get('region')}, {ip_info.get('country')}")
    else:
        st.info("Could not retrieve public IP/ISP info.")
    
    # DNS SERVERS
    st.subheader("DNS Servers")
    dns_servers = parse_dns_from_ipconfig()
    if dns_servers:
        for d in dns_servers:
            st.write(d)
    else:
        st.info("No DNS servers found.")
    
    # NETWORK ADAPTERS
    st.markdown("---")
    st.subheader("Network Adapters")
    adapters = parse_ipconfig_adapters()
    if adapters:
        internet_ok = is_internet_reachable()
        st.write(f"**Internet reachable:** {'Yes' if internet_ok else 'No'}")
        connected_rows = []
        for a in adapters:
            name = a.get("name")
            media = a.get("media_state") or ""
            ipv4 = a.get("ipv4") or ""
            gw = a.get("default_gateway") or ""
            connected = False
            if media and "disconnected" in media.lower():
                connected = False
            elif ipv4 and gw:
                connected = True
            elif ipv4 and internet_ok:
                connected = True
            connected_rows.append({
                "Adapter": name,
                "IPv4": ipv4,
                "Gateway": gw,
                "State": media,
                "Connected": "Yes" if connected else "No"
            })
        st.dataframe(pd.DataFrame(connected_rows), use_container_width=True)
    
    # NETWORK COMMANDS
    st.markdown("---")
    st.subheader("Network Commands")
    
    if st.button("Flush DNS (ipconfig /flushdns)", key="btn_flush_dns"):
        rc, out, err = run_cmd_capture(["ipconfig", "/flushdns"])
        if rc == 0:
            st.success(out.strip())
        else:
            st.warning("Flush DNS failed.")
            st.text(err)
    
    if st.button("Reset IP (netsh int ip reset)", key="btn_reset_ip"):
        st.info("This will run netsh int ip reset. Admin prompt will appear.")
        run_elevated_cmd(r"netsh int ip reset C:\resetlog.txt")
    
    if st.button("Reset Winsock (netsh winsock reset)", key="btn_reset_winsock"):
        st.info("This will reset Winsock. A reboot may be required.")
        run_elevated_cmd("netsh winsock reset")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ipconfig /release", key="btn_ipconfig_release"):
            st.info("Releasing IP addresses.")
            rc, out, err = run_cmd_capture(["ipconfig", "/release"])
            if rc == 0:
                st.success("Released IP addresses.")
            else:
                st.warning("Release failed.")
    with col2:
        if st.button("ipconfig /renew", key="btn_ipconfig_renew"):
            st.info("Renewing IP addresses.")
            rc, out, err = run_cmd_capture(["ipconfig", "/renew"])
            if rc == 0:
                st.success("Renewed IP addresses.")
            else:
                st.warning("Renew failed.")
    
    # NETWORK STATISTICS
    st.markdown("---")
    st.subheader("Network Interface Statistics")
    net_stats = get_network_stats()
    if not net_stats.empty:
        st.dataframe(net_stats, use_container_width=True)
    
    # SPEEDTEST (NO EXTERNAL MODULE REQUIRED)
    st.markdown("---")
    st.subheader("Speed Test (robust mode)")
    st.caption("✅ No extra modules required — uses built-in Python libraries only.")

    def _run_builtin_speedtest():
        """
        Pure-Python speed test using only stdlib (urllib, socket, time).
        - Ping  : TCP round-trip to 8.8.8.8:53  (5 probes, median)
        - Download: fetch a 10 MB file from a public CDN, measure throughput
        - Upload  : POST ~5 MB of random data to httpbin.org, measure throughput
        Returns dict with keys: ping_ms, download_mbps, upload_mbps, error
        """
        import urllib.request
        import socket, time, os

        results = {"ping_ms": None, "download_mbps": None, "upload_mbps": None, "error": None}

        # ── PING ─────────────────────────────────────────────────────────────
        ping_host, ping_port = "8.8.8.8", 53
        ping_samples = []
        for _ in range(5):
            try:
                t0 = time.perf_counter()
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect((ping_host, ping_port))
                s.close()
                ping_samples.append((time.perf_counter() - t0) * 1000)
            except Exception:
                pass
            time.sleep(0.1)
        if ping_samples:
            ping_samples.sort()
            results["ping_ms"] = round(ping_samples[len(ping_samples) // 2], 2)

        # ── DOWNLOAD ─────────────────────────────────────────────────────────
        # Cloudflare speed.cloudflare.com provides stable test files
        download_urls = [
            "https://speed.cloudflare.com/__down?bytes=10000000",   # 10 MB via Cloudflare
            "http://speedtest.tele2.net/10MB.zip",                  # fallback
        ]
        for url in download_urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                t0 = time.perf_counter()
                total = 0
                with urllib.request.urlopen(req, timeout=30) as resp:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        total += len(chunk)
                elapsed = time.perf_counter() - t0
                if elapsed > 0 and total > 0:
                    results["download_mbps"] = round((total * 8) / elapsed / 1_000_000, 2)
                    break
            except Exception:
                continue

        # ── UPLOAD ───────────────────────────────────────────────────────────
        # POST random data to httpbin.org/post (reliable public echo endpoint)
        upload_urls = [
            "https://httpbin.org/post",
            "https://postman-echo.com/post",
        ]
        upload_size = 5 * 1024 * 1024  # 5 MB
        upload_data = os.urandom(upload_size)
        for url in upload_urls:
            try:
                req = urllib.request.Request(
                    url,
                    data=upload_data,
                    method="POST",
                    headers={
                        "Content-Type": "application/octet-stream",
                        "User-Agent": "Mozilla/5.0",
                        "Content-Length": str(upload_size),
                    }
                )
                t0 = time.perf_counter()
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp.read()
                elapsed = time.perf_counter() - t0
                if elapsed > 0:
                    results["upload_mbps"] = round((upload_size * 8) / elapsed / 1_000_000, 2)
                    break
            except Exception:
                continue

        if results["download_mbps"] is None and results["upload_mbps"] is None:
            results["error"] = "Could not reach test servers. Check your internet connection."

        return results

    if st.button("▶️ Run Speed Test", key="btn_run_speedtest"):
        with st.spinner("Testing your connection speed... (may take 20–40 seconds)"):
            res = _run_builtin_speedtest()

        if res["error"]:
            st.error(res["error"])
        else:
            st.success("✅ Speed test completed!")
            r1, r2, r3 = st.columns(3)
            with r1:
                ping_val = f"{res['ping_ms']} ms" if res["ping_ms"] is not None else "N/A"
                st.metric("📡 Ping (latency)", ping_val)
            with r2:
                dl_val = f"{res['download_mbps']} Mbps" if res["download_mbps"] is not None else "N/A"
                st.metric("⬇️ Download", dl_val)
            with r3:
                ul_val = f"{res['upload_mbps']} Mbps" if res["upload_mbps"] is not None else "N/A"
                st.metric("⬆️ Upload", ul_val)

            if PLOTLY_AVAILABLE and any(v is not None for v in [res["download_mbps"], res["upload_mbps"]]):
                bar_labels, bar_vals, bar_colors = [], [], []
                if res["download_mbps"] is not None:
                    bar_labels.append("Download")
                    bar_vals.append(res["download_mbps"])
                    bar_colors.append("#2196F3")
                if res["upload_mbps"] is not None:
                    bar_labels.append("Upload")
                    bar_vals.append(res["upload_mbps"])
                    bar_colors.append("#4CAF50")
                fig = go.Figure(go.Bar(
                    x=bar_labels, y=bar_vals,
                    marker_color=bar_colors,
                    text=[f"{v} Mbps" for v in bar_vals],
                    textposition="outside"
                ))
                fig.update_layout(
                    title="Speed Test Results",
                    yaxis_title="Mbps",
                    yaxis=dict(range=[0, max(bar_vals) * 1.3]),
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)

            st.caption("Download tested via Cloudflare (10 MB). Upload tested via httpbin.org (5 MB). "
                       "Results may differ slightly from dedicated speed-test sites.")

# ============================================================================
# TAB 7: EVENT VIEWER (COMPLETE - RESTORED)
# ============================================================================

with tabs[6]:
    st.header("Event Viewer — Errors Only")
    
    if platform.system() != "Windows":
        st.info("Event Viewer is supported only on Windows.")
    else:
        st.markdown(
            "Shows **Error** level events grouped by log (Application, System). "
            "Adjust the time window and maximum events to fetch."
        )
        
        col_a, col_b, col_c = st.columns([2, 1, 1])
        with col_a:
            time_window_minutes = st.number_input("Time window (minutes, 0 = all recent)", min_value=0, max_value=1440, value=60, key="ev_time_window")
        with col_b:
            max_events = st.number_input("Max events to fetch", min_value=10, max_value=5000, value=500, step=10, key="ev_max_events")
        with col_c:
            refresh_ev = st.button("🔁 Refresh Events", key="btn_ev_refresh")
        
        default_logs = ["Application", "System", "Security", "Setup", "ForwardedEvents"]
        logs_input = st.multiselect("Event logs to include", default_logs, default=default_logs, key="ev_logs")
        
        logs_quoted = ",".join("'" + l.replace("'", "''") + "'" for l in logs_input) if logs_input else "'Application'"
        
        if time_window_minutes and time_window_minutes > 0:
            ps_cmd_non_elev = (
                "$start = (Get-Date).AddMinutes(-{minutes}); "
                "Get-WinEvent -LogName {logs} -MaxEvents {max} -ErrorAction SilentlyContinue | "
                "Where-Object {{ ($_.TimeCreated -ge $start) -and ($_.LevelDisplayName -eq 'Error') }} | "
                "Select-Object TimeCreated, LogName, ProviderName, Id, LevelDisplayName, Message | ConvertTo-Json -Depth 6"
            ).format(minutes=int(time_window_minutes), logs=logs_quoted, max=int(max_events))
        else:
            ps_cmd_non_elev = (
                "Get-WinEvent -LogName {logs} -MaxEvents {max} -ErrorAction SilentlyContinue | "
                "Where-Object {{ $_.LevelDisplayName -eq 'Error' }} | "
                "Select-Object TimeCreated, LogName, ProviderName, Id, LevelDisplayName, Message | ConvertTo-Json -Depth 6"
            ).format(logs=logs_quoted, max=int(max_events))
        
        if refresh_ev or "ev_last_run" not in st.session_state:
            st.session_state["ev_last_run"] = time.time()
            with st.spinner("Querying Windows Event Log (errors only)..."):
                rc, out, err = run_cmd_capture(["powershell", "-NoProfile", "-Command", ps_cmd_non_elev])
                
                if rc == 0 and out:
                    try:
                        parsed = json.loads(out)
                        if isinstance(parsed, dict):
                            parsed = [parsed]
                        
                        if parsed:
                            df = pd.DataFrame(parsed)
                            for col in ["TimeCreated", "LogName", "ProviderName", "Id", "LevelDisplayName", "Message"]:
                                if col not in df.columns:
                                    df[col] = None
                            
                            df["TimeCreated"] = df["TimeCreated"].apply(parse_dotnet_date)
                            try:
                                df["TimeCreated"] = pd.to_datetime(df["TimeCreated"])
                            except Exception:
                                pass
                            
                            st.session_state["ev_events"] = df
                        else:
                            st.session_state["ev_events"] = pd.DataFrame()
                    except Exception as e:
                        st.error(f"Failed to parse event output: {e}")
                        st.session_state["ev_events"] = pd.DataFrame()
                else:
                    st.warning("Could not retrieve events. No error events found in the selected time window.")
                    st.session_state["ev_events"] = pd.DataFrame()
        
        ev_df = st.session_state.get("ev_events", pd.DataFrame())
        
        if isinstance(ev_df, pd.DataFrame) and not ev_df.empty:
            display_df = ev_df.copy()
            
            # Create readable time column
            display_df["TimeCreatedStr"] = display_df["TimeCreated"].apply(format_time_for_export)
            display_df["Message"] = display_df["Message"].astype(str).fillna("")
            display_df["LogName"] = display_df["LogName"].fillna("").astype(str)
            display_df["LogNameNormalized"] = display_df["LogName"].apply(lambda x: x if x.strip() else "<Other>")
            
            # Get unique logs
            logs_found = sorted(list(display_df["LogNameNormalized"].unique()))
            
            # Sort by log then time
            try:
                if pd.api.types.is_datetime64_any_dtype(display_df["TimeCreated"]):
                    display_df = display_df.sort_values(by=["LogNameNormalized", "TimeCreated"], ascending=[True, False]).reset_index(drop=True)
                else:
                    display_df = display_df.sort_values(by=["LogNameNormalized", "TimeCreatedStr"], ascending=[True, False]).reset_index(drop=True)
            except Exception:
                display_df = display_df.reset_index(drop=True)
            
            # Show per-log tables
            for log in logs_found:
                st.subheader(f"{log} — Errors")
                sub = display_df[display_df["LogNameNormalized"] == log].copy()
                
                table_df = sub[["TimeCreatedStr", "ProviderName", "Id", "LevelDisplayName", "Message"]].rename(
                    columns={
                        "TimeCreatedStr": "Time",
                        "ProviderName": "Source",
                        "Id": "Event ID",
                        "LevelDisplayName": "Level",
                        "Message": "Message"
                    }
                )
                st.dataframe(table_df, use_container_width=True, height=360)
            
            # CSV export
            st.markdown("---")
            try:
                export_df = display_df[["TimeCreatedStr", "LogNameNormalized", "ProviderName", "Id", "LevelDisplayName", "Message"]].rename(
                    columns={
                        "TimeCreatedStr": "TimeCreated",
                        "LogNameNormalized": "LogName",
                        "ProviderName": "ProviderName",
                        "Id": "Id",
                        "LevelDisplayName": "LevelDisplayName",
                        "Message": "Message"
                    }
                )
                export_df = export_df.sort_values(by=["LogName", "TimeCreated"], ascending=[True, False]).reset_index(drop=True)
                csv_bytes = export_df.to_csv(index=False, quoting=_csv.QUOTE_ALL).encode("utf-8")
                st.download_button(
                    label="📥 Download events as CSV",
                    data=csv_bytes,
                    file_name="event_errors_grouped.csv",
                    mime="text/csv",
                    key="btn_ev_download_csv"
                )
            except Exception as e:
                st.error(f"Failed to prepare CSV: {e}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Open Event Viewer (eventvwr)", key="btn_ev_open_viewer"):
                    try:
                        # Run Event Viewer with elevation
                        import ctypes
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", "eventvwr.msc", None, None, 1)
                        st.success("Event Viewer opened!")
                    except Exception as e:
                        st.error(f"Could not open Event Viewer: {e}")
            with col2:
                if st.button("Refresh table", key="btn_ev_refresh_table"):
                    if "ev_last_run" in st.session_state:
                        del st.session_state["ev_last_run"]
                    if "ev_events" in st.session_state:
                        del st.session_state["ev_events"]
        else:
            st.info("No error events found in the selected logs/time window.")

# ============================================================================
# TAB 8: RECENT ACTIVITY
# ============================================================================

with tabs[7]:
    st.header("Recent System Activity")
    
    activity_tab1, activity_tab2 = st.tabs(["📂 Files", "📦 Programs"])
    
    with activity_tab1:
        st.subheader("Recently Modified/Created Files")
        
        time_range = st.radio("Time Range", ["Past Day", "Past Week"], horizontal=True)
        file_mode = st.radio("File Type", ["Modified", "Created"], horizontal=True)
        
        days = 1 if time_range == "Past Day" else 7
        mode = "modified" if file_mode == "Modified" else "created"
        
        if st.button(f"Scan for {file_mode} Files", key="btn_11"):
            with st.spinner("Scanning..."):
                files_df = get_recent_files(os.path.expanduser("~"), days=days, mode=mode, max_depth=2, limit=100)
                if not files_df.empty:
                    st.dataframe(files_df, use_container_width=True)
                    st.caption(f"Found {len(files_df)} files")
                else:
                    st.info("No files found matching criteria")
    
    with activity_tab2:
        st.subheader("Recently Installed Programs")
        
        prog_time_range = st.radio("Programs Time Range", ["Past Day", "Past Week"], 
                                   horizontal=True, key="prog_time")
        prog_days = 1 if prog_time_range == "Past Day" else 7
        
        if st.button("Scan for Installed Programs", key="btn_12"):
            with st.spinner("Scanning..."):
                programs_df = get_recent_installed_programs(days=prog_days)
                if not programs_df.empty:
                    st.dataframe(programs_df, use_container_width=True)
                    st.caption(f"Found {len(programs_df)} programs")
                else:
                    st.info("No recently installed programs found")

# ============================================================================
# TAB 9: HARDWARE MONITOR
# ============================================================================

with tabs[8]:
    st.header("🌡️ Hardware Health Monitor")
    
    hw_col1, hw_col2, hw_col3 = st.columns(3)
    
    with hw_col1:
        st.subheader("CPU Temperature")
        cpu_temps = get_cpu_temperature()
        
        if cpu_temps:
            for temp in cpu_temps:
                temp_color = "🟢" if temp['current'] < 60 else "🟡" if temp['current'] < 80 else "🔴"
                st.metric(
                    f"{temp_color} {temp['name']}",
                    f"{temp['current']:.1f}°C",
                    delta=f"High: {temp['high']:.1f}°C" if temp['high'] else None
                )
        else:
            st.info("Temperature sensors not available")
            st.caption("Install OpenHardwareMonitor or enable WMI access")
    
    with hw_col2:
        st.subheader("GPU Status")
        gpu_info = get_gpu_info()
        
        if gpu_info:
            for gpu in gpu_info:
                temp_color = "🟢" if gpu['temp'] < 70 else "🟡" if gpu['temp'] < 85 else "🔴"
                st.metric(f"{temp_color} {gpu['name']}", f"{gpu['temp']:.1f}°C")
                st.progress(gpu['load'] / 100, text=f"Load: {gpu['load']:.1f}%")
                st.caption(f"Memory: {gpu['memory_used']:.0f}MB / {gpu['memory_total']:.0f}MB")
        else:
            st.info("GPU not detected")
            st.caption("Install GPUtil: pip install gputil")
    
    with hw_col3:
        st.subheader("System Fans")
        st.info("Fan speed monitoring")
        st.caption("Requires OpenHardwareMonitor integration")
        
        # CPU frequency as alternative
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            st.metric("CPU Frequency", f"{cpu_freq.current:.0f} MHz")
            st.caption(f"Min: {cpu_freq.min:.0f} MHz | Max: {cpu_freq.max:.0f} MHz")
    
    st.divider()
    
    # CPU per-core usage
    st.subheader("CPU Core Usage")
    cpu_cores = current_metrics['cpu_per_core']
    
    if PLOTLY_AVAILABLE:
        fig = go.Figure(data=[
            go.Bar(x=[f"Core {i}" for i in range(len(cpu_cores))], y=cpu_cores)
        ])
        fig.update_layout(
            title="CPU Usage per Core",
            xaxis_title="Core",
            yaxis_title="Usage (%)",
            yaxis=dict(range=[0, 100])
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        core_df = pd.DataFrame({
            'Core': [f"Core {i}" for i in range(len(cpu_cores))],
            'Usage %': cpu_cores
        })
        st.dataframe(core_df, use_container_width=True)

# ============================================================================
# TAB 10: BATTERY & POWER
# ============================================================================

with tabs[9]:
    st.header("🔋 Battery & Power Management")
    
    battery = get_battery_info()
    
    if battery:
        # Battery status
        batt_col1, batt_col2, batt_col3 = st.columns(3)
        
        with batt_col1:
            st.metric("Battery Level", f"{battery['percent']:.0f}%")
        
        with batt_col2:
            status_icon = "🔌" if battery['power_plugged'] else "🔋"
            st.metric(f"{status_icon} Status", battery['status'])
        
        with batt_col3:
            if battery['time_left']:
                st.metric("Time Remaining", battery['time_left_str'])
            else:
                st.metric("Time Remaining", "Calculating...")
        
        # Battery gauge
        if PLOTLY_AVAILABLE:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=battery['percent'],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Battery Level"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "green" if battery['percent'] > 50 else "orange" if battery['percent'] > 20 else "red"},
                    'steps': [
                        {'range': [0, 20], 'color': "lightcoral"},
                        {'range': [20, 50], 'color': "lightyellow"},
                        {'range': [50, 100], 'color': "lightgreen"}
                    ],
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Battery report
        st.subheader("Generate Battery Report")
        if st.button("📊 Generate Windows Battery Report", key="btn_13"):
            report_path = generate_battery_report()
            if report_path:
                st.success(f"Report generated: {report_path}")
                if st.button("Open Report", key="btn_14"):
                    import webbrowser
                    webbrowser.open(f"file:///{report_path}")
            else:
                st.error("Could not generate battery report")
    else:
        st.info("🔌 No battery detected - System is running on AC power")
        st.write("This device appears to be a desktop computer or the battery information is not available.")

# ============================================================================
# TAB 11: ALERTS & LOGS
# ============================================================================

with tabs[10]:
    st.header("🔔 Alerts & Activity Logs")
    
    alert_tab1, alert_tab2 = st.tabs(["Active Alerts", "Alert History"])
    
    with alert_tab1:
        st.subheader("Current System Alerts")
        
        if alerts:
            for alert_type, msg, severity in alerts:
                severity_icon = "🚨" if severity == "critical" else "⚠️"
                st.warning(f"{severity_icon} **{alert_type.upper()}**: {msg}")
        else:
            st.success("✅ No active alerts - All systems normal")
        
        st.divider()
        
        # Alert statistics
        st.subheader("Alert Statistics (24h)")
        alerts_df = st.session_state.db.get_alerts(hours=24)
        
        if not alerts_df.empty:
            alert_counts = alerts_df['alert_type'].value_counts()
            
            if PLOTLY_AVAILABLE:
                fig = px.bar(
                    x=alert_counts.index,
                    y=alert_counts.values,
                    labels={'x': 'Alert Type', 'y': 'Count'},
                    title='Alerts by Type (Last 24 Hours)'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.metric("Total Alerts (24h)", len(alerts_df))
        else:
            st.info("No alerts in the last 24 hours")
    
    with alert_tab2:
        st.subheader("Alert History")
        
        history_hours = st.slider("Show alerts from last X hours", 1, 168, 24)
        alerts_history = st.session_state.db.get_alerts(hours=history_hours)
        
        if not alerts_history.empty:
            st.dataframe(alerts_history, use_container_width=True)
            
            # Export
            csv = alerts_history.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Alert History (CSV)",
                data=csv,
                file_name=f'alert_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv'
            )
        else:
            st.info(f"No alerts found in the last {history_hours} hours")

# ============================================================================
# TAB 12: BENCHMARKS
# ============================================================================

with tabs[11]:
    st.header("🏃 System Benchmarks")
    
    st.write("Run performance benchmarks to test your system's capabilities")
    
    bench_col1, bench_col2 = st.columns(2)
    
    with bench_col1:
        st.subheader("CPU Benchmark")
        cpu_iterations = st.slider("Iterations", 1, 20, 5, key="cpu_iter")
        
        if st.button("▶️ Run CPU Benchmark", type="primary", key="btn_15"):
            with st.spinner("Running CPU benchmark..."):
                result = benchmark_cpu(iterations=cpu_iterations)
                
                if result['status'] == 'completed':
                    st.success(f"✅ Benchmark completed!")
                    st.metric("CPU Score", f"{result['score']:.2f}")
                    st.caption(f"Time: {result['time_seconds']:.2f}s for {result['iterations']} iterations")
                    
                    # Save to database
                    st.session_state.db.log_benchmark('cpu', result['score'], 
                                                     f"iterations={result['iterations']}")
                else:
                    st.error(f"Benchmark failed: {result['status']}")
        
        st.divider()
        
        st.subheader("Memory Benchmark")
        mem_size = st.slider("Test size (MB)", 10, 500, 100, key="mem_size")
        
        if st.button("▶️ Run Memory Benchmark", type="primary", key="btn_16"):
            with st.spinner("Running memory benchmark..."):
                result = benchmark_memory(size_mb=mem_size)
                
                if result['status'] == 'completed':
                    st.success("✅ Benchmark completed!")
                    st.metric("Read Speed", f"{result['read_speed_mbps']:.2f} MB/s")
                    st.metric("Write Speed", f"{result['write_speed_mbps']:.2f} MB/s")
                    
                    # Save to database
                    st.session_state.db.log_benchmark('memory', 
                                                     result['read_speed_mbps'],
                                                     f"write_speed={result['write_speed_mbps']}")
                else:
                    st.error(f"Benchmark failed: {result['status']}")
    
    with bench_col2:
        st.subheader("Disk Benchmark")
        disk_size = st.slider("Test size (MB)", 10, 500, 100, key="disk_size")
        
        if st.button("▶️ Run Disk Benchmark", type="primary", key="btn_17"):
            with st.spinner("Running disk benchmark..."):
                result = benchmark_disk(test_size_mb=disk_size)
                
                if result['status'] == 'completed':
                    st.success("✅ Benchmark completed!")
                    st.metric("Read Speed", f"{result['read_speed_mbps']:.2f} MB/s")
                    st.metric("Write Speed", f"{result['write_speed_mbps']:.2f} MB/s")
                    
                    # Save to database
                    st.session_state.db.log_benchmark('disk',
                                                     result['read_speed_mbps'],
                                                     f"write_speed={result['write_speed_mbps']}")
                else:
                    st.error(f"Benchmark failed: {result['status']}")
        
        st.divider()
        
        st.subheader("Network Test")
        
        if st.button("▶️ Run Network Test", type="primary", key="btn_18"):
            with st.spinner("Testing network..."):
                result = benchmark_network()
                
                if result['status'] == 'completed':
                    st.success("✅ Test completed!")
                    st.metric("Latency to 8.8.8.8", f"{result['latency_ms']:.2f} ms")
                    
                    # Save to database
                    st.session_state.db.log_benchmark('network', result['latency_ms'])
                else:
                    st.error(f"Test failed: {result['status']}")
    
    st.divider()
    
    # Benchmark history
    st.subheader("Benchmark History")
    bench_history = st.session_state.db.get_benchmarks()
    
    if not bench_history.empty:
        st.dataframe(bench_history, use_container_width=True)
        
        # Visualize
        if PLOTLY_AVAILABLE and len(bench_history) > 0:
            bench_history['timestamp'] = pd.to_datetime(bench_history['timestamp'])
            
            for bench_type in bench_history['benchmark_type'].unique():
                type_data = bench_history[bench_history['benchmark_type'] == bench_type]
                fig = px.line(type_data, x='timestamp', y='score',
                            title=f'{bench_type.upper()} Benchmark History')
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No benchmark history available. Run some benchmarks to see results here.")

# ============================================================================
# TAB 13: SYSTEM INFORMATION
# ============================================================================

with tabs[12]:
    st.header("💻 Detailed System Information")
    
    sys_info = get_detailed_system_info()
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.subheader("Operating System")
        st.write(f"**OS:** {sys_info['OS']}")
        st.write(f"**Version:** {sys_info['OS Version']}")
        st.write(f"**Release:** {sys_info['OS Release']}")
        st.write(f"**Architecture:** {sys_info['Architecture']}")
        st.write(f"**Hostname:** {sys_info['Hostname']}")
        
        st.divider()
        
        st.subheader("Processor")
        st.write(f"**CPU:** {sys_info['Processor']}")
        st.write(f"**Physical Cores:** {sys_info['CPU Cores (Physical)']}")
        st.write(f"**Logical Cores:** {sys_info['CPU Cores (Logical)']}")
        st.write(f"**Frequency:** {sys_info['CPU Frequency']}")
    
    with info_col2:
        st.subheader("Memory")
        st.write(f"**Total RAM:** {sys_info['Total RAM']}")
        st.write(f"**Available RAM:** {sys_info['Available RAM']}")
        
        st.divider()
        
        st.subheader("Storage")
        st.write(f"**Total Disk:** {sys_info['Total Disk']}")
        st.write(f"**Free Disk:** {sys_info['Free Disk']}")
        
        st.divider()
        
        st.subheader("System")
        st.write(f"**Boot Time:** {sys_info['Boot Time']}")
        st.write(f"**Python Version:** {sys_info['Python Version']}")
    
    st.divider()
    
    # Export system info
    if st.button("📥 Export System Information", key="btn_19"):
        report = "SYSTEM INFORMATION REPORT\n"
        report += "=" * 50 + "\n\n"
        
        for key, value in sys_info.items():
            report += f"{key}: {value}\n"
        
        report += "\n" + "=" * 50 + "\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        st.download_button(
            label="Download Report",
            data=report,
            file_name=f"system_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

# ============================================================================
# TAB 14: NETWORK CONNECTIONS
# ============================================================================

with tabs[13]:
    st.header("🔌 Active Network Connections")
    
    connections_df = get_network_connections()
    
    if not connections_df.empty:
        # Filters
        conn_col1, conn_col2 = st.columns(2)
        
        with conn_col1:
            filter_process = st.text_input("Filter by process", "")
        
        with conn_col2:
            filter_status = st.multiselect("Filter by status", 
                                          connections_df['Status'].unique(),
                                          default=connections_df['Status'].unique())
        
        # Apply filters
        filtered_df = connections_df[connections_df['Status'].isin(filter_status)]
        
        if filter_process:
            filtered_df = filtered_df[filtered_df['Process'].str.contains(filter_process, case=False, na=False)]
        
        st.dataframe(filtered_df, use_container_width=True, height=500)
        st.caption(f"Showing {len(filtered_df)} of {len(connections_df)} connections")
        
        # Statistics
        st.divider()
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        
        with stat_col1:
            st.metric("Total Connections", len(connections_df))
        
        with stat_col2:
            established = len(connections_df[connections_df['Status'] == 'ESTABLISHED'])
            st.metric("Established", established)
        
        with stat_col3:
            unique_processes = connections_df['Process'].nunique()
            st.metric("Unique Processes", unique_processes)
        
        # Connection by process chart
        if PLOTLY_AVAILABLE:
            st.subheader("Connections by Process")
            process_counts = connections_df['Process'].value_counts().head(10)
            fig = px.bar(x=process_counts.index, y=process_counts.values,
                        labels={'x': 'Process', 'y': 'Connection Count'},
                        title='Top 10 Processes by Connection Count')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No active network connections found")

# ============================================================================
# TAB 15: SERVICES & TASKS
# ============================================================================

with tabs[14]:
    st.header("⚙️ Windows Services & Scheduled Tasks")
    
    if WINDOWS:
        service_tab1, service_tab2 = st.tabs(["Services", "Scheduled Tasks"])
        
        with service_tab1:
            st.subheader("Windows Services")
            
            if st.button("🔄 Load Services", key="btn_20"):
                with st.spinner("Loading services..."):
                    services_df = get_windows_services()
                    
                    if not services_df.empty:
                        # Filters
                        service_col1, service_col2 = st.columns(2)
                        
                        with service_col1:
                            filter_state = st.multiselect("Filter by state",
                                                         services_df['State'].unique(),
                                                         default=['Running'])
                        
                        with service_col2:
                            filter_name = st.text_input("Filter by name", "", key="svc_filter")
                        
                        # Apply filters
                        filtered_services = services_df[services_df['State'].isin(filter_state)]
                        
                        if filter_name:
                            filtered_services = filtered_services[
                                filtered_services['Display Name'].str.contains(filter_name, case=False, na=False) |
                                filtered_services['Name'].str.contains(filter_name, case=False, na=False)
                            ]
                        
                        st.dataframe(filtered_services, use_container_width=True, height=500)
                        st.caption(f"Showing {len(filtered_services)} of {len(services_df)} services")
                    else:
                        st.error("Could not load services. WMI might not be available.")
        
        with service_tab2:
            st.subheader("Scheduled Tasks")
            st.info("Scheduled tasks information")
            
            if st.button("Open Task Scheduler", key="btn_21"):
                try:
                    subprocess.Popen(['taskschd.msc'])
                except:
                    st.error("Could not open Task Scheduler")
    else:
        st.warning("Services & Tasks feature is only available on Windows")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with footer_col2:
    st.caption(f"🖥️ Monitoring: {socket.gethostname()}")

with footer_col3:
    if st.button("ℹ️ About", key="btn_22"):
        st.info("""
        **Enhanced System Monitor v2.0**
        
        Professional-grade system monitoring tool with:
        - Real-time hardware monitoring
        - Battery health tracking
        - Automated alerts
        - Performance benchmarks
        - Historical data analysis
        - Network diagnostics
        - Process management
        
        Built with Streamlit, psutil, and Python
        """)

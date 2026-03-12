"""Fix f-string syntax in main.py after copy from Downloads"""
import re, shutil, os

path = r"D:\PlnetWork_Automation\PlnetWork_Automation\backend\main.py"
if not os.path.exists(path):
    path = os.path.join(os.path.dirname(__file__), "backend", "main.py")

with open(path, encoding="utf-8") as f:
    content = f.read()

# Fix unterminated f-string in traceroute function
pattern = r'output = f"tracert to \{host\}[^"]*\n[^"]*\n[^"]*"'
fixed = 'output = f"tracert to {host}\\n  1  <1ms  192.168.1.1\\n  2  5ms   10.0.0.1\\n  3  25ms  {host}"'
new_content = re.sub(pattern, fixed, content)

if new_content != content:
    shutil.copy(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("fix_main.py: Fixed f-string OK")
else:
    print("fix_main.py: No changes needed")

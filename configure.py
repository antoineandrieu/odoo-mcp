#!/usr/bin/env python3
"""
Odoo MCP Server - Configuration Generator

This script helps generate the Claude Desktop configuration
for the Odoo MCP server with proper paths and credentials.
"""

import json
import platform
import sys
from pathlib import Path


def get_venv_python_path() -> Path:
    """Get the path to Python in the virtual environment."""
    script_dir = Path(__file__).parent
    venv_dir = script_dir / ".venv"
    
    if platform.system() == "Windows":
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"
    
    if not python_path.exists():
        print(f"⚠️  Warning: Virtual environment not found at {venv_dir}")
        print("   Run ./install.sh first or create it manually:")
        print("   python3 -m venv .venv")
        print("   pip install -e .")
        sys.exit(1)
    
    return python_path.absolute()


def get_claude_config_path() -> Path:
    """Get the Claude Desktop config file path for the current OS."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        config_path = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:  # Linux and others
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    return config_path


def get_odoo_credentials() -> dict[str, str]:
    """Prompt user for Odoo credentials."""
    print("\n📋 Odoo Instance Configuration")
    print("=" * 50)
    
    while True:
        odoo_url = input("\n🌐 Odoo URL (e.g., https://mycompany.odoo.com): ").strip()
        if odoo_url:
            if not odoo_url.startswith(("http://", "https://")):
                print("   ⚠️  URL should start with http:// or https://")
                continue
            break
        print("   ❌ URL is required")
    
    while True:
        odoo_db = input("🗄️  Database name: ").strip()
        if odoo_db:
            break
        print("   ❌ Database name is required")
    
    while True:
        username = input("👤 Username: ").strip()
        if username:
            break
        print("   ❌ Username is required")
    
    while True:
        password = input("🔑 Password: ").strip()
        if password:
            break
        print("   ❌ Password is required")
    
    # Optional settings with defaults
    print("\n⚙️  Optional Settings (press Enter for defaults)")
    timeout = input("⏱️  Timeout in seconds [30]: ").strip() or "30"
    verify_ssl = input("🔒 Verify SSL certificates? (true/false) [true]: ").strip() or "true"
    
    return {
        "ODOO_URL": odoo_url,
        "ODOO_DB": odoo_db,
        "ODOO_USERNAME": username,
        "ODOO_PASSWORD": password,
        "ODOO_TIMEOUT": timeout,
        "ODOO_VERIFY_SSL": verify_ssl,
    }


def generate_config(credentials: dict[str, str]) -> dict:
    """Generate the Claude Desktop configuration."""
    python_path = get_venv_python_path()
    
    # Convert Windows paths to use forward slashes for JSON
    if platform.system() == "Windows":
        python_path_str = str(python_path).replace("\\", "/")
    else:
        python_path_str = str(python_path)
    
    config = {
        "mcpServers": {
            "odoo": {
                "command": python_path_str,
                "args": ["-m", "odoo_mcp.mcp_server"],
                "env": credentials
            }
        }
    }
    
    return config


def display_config(config: dict) -> None:
    """Display the generated configuration."""
    print("\n" + "=" * 50)
    print("✅ Configuration Generated Successfully!")
    print("=" * 50)
    
    config_path = get_claude_config_path()
    
    print(f"\n📁 Claude Desktop Config Location:")
    print(f"   {config_path}")
    
    if config_path.exists():
        print("   ✓ File exists")
    else:
        print("   ⚠️  File doesn't exist yet (will be created)")
    
    print("\n📋 Configuration to Add:")
    print("-" * 50)
    print(json.dumps(config, indent=2))
    print("-" * 50)
    
    print("\n📝 Next Steps:")
    print("1. Open Claude Desktop config file:")
    print(f"   {config_path}")
    print("\n2. If the file is empty or doesn't exist, paste the entire configuration above")
    print("\n3. If the file already has content, merge the 'odoo' entry into the")
    print("   existing 'mcpServers' section")
    print("\n4. Save the file and restart Claude Desktop")
    print("\n5. Test by asking Claude: \"Can you ping the Odoo server?\"")


def save_to_file(config: dict) -> None:
    """Optionally save configuration to a file."""
    print("\n💾 Save Configuration")
    save = input("Would you like to save this config to a file? (y/N): ").strip().lower()
    
    if save == 'y':
        output_file = Path("claude_config.json")
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✓ Configuration saved to: {output_file.absolute()}")
        print(f"  You can copy this to: {get_claude_config_path()}")


def check_existing_config() -> None:
    """Check if Claude Desktop config already exists and warn about merging."""
    config_path = get_claude_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                existing = json.load(f)
            
            if 'mcpServers' in existing and 'odoo' in existing.get('mcpServers', {}):
                print("\n⚠️  WARNING: An 'odoo' server is already configured in Claude Desktop!")
                print("   The new configuration will replace the existing one.")
                proceed = input("   Continue? (y/N): ").strip().lower()
                if proceed != 'y':
                    print("Configuration cancelled.")
                    sys.exit(0)
        except json.JSONDecodeError:
            print("\n⚠️  Note: Existing config file has invalid JSON. Backup recommended.")


def main() -> None:
    """Main configuration flow."""
    print("🔧 Odoo MCP Server - Configuration Generator")
    print("=" * 50)
    print("\nThis tool will help you configure the Odoo MCP server")
    print("for use with Claude Desktop.")
    
    # Check for existing configuration
    check_existing_config()
    
    # Get credentials
    credentials = get_odoo_credentials()
    
    # Generate configuration
    config = generate_config(credentials)
    
    # Display results
    display_config(config)
    
    # Optionally save to file
    save_to_file(config)
    
    print("\n" + "=" * 50)
    print("✨ Configuration complete! Happy chatting with Odoo! 🚀")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Configuration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

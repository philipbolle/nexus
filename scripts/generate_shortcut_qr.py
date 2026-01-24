#!/usr/bin/env python3
"""
Generate QR code for iPhone Quick Expense Shortcut.

This script creates a QR code that can be scanned by iPhone to
easily create the Quick Expense shortcut.

Note: iOS Shortcuts doesn't have a direct import via QR code,
but this generates a QR code with installation instructions.
"""

import qrcode
import json
import os
from pathlib import Path

def generate_qr_code():
    """Generate QR code for shortcut installation."""

    # Installation instructions URL
    # Since iOS Shortcuts doesn't support direct QR import,
    # we'll create a QR code that opens a webpage with instructions
    # or use a data URL with the shortcut configuration

    # Create a simple HTML page with the shortcut configuration
    # that can be opened on iPhone
    shortcut_config = {
        "name": "Quick Expense",
        "actions": [
            {
                "type": "ask",
                "config": {
                    "question": "Amount?",
                    "defaultAnswer": "",
                    "type": "Number"
                }
            },
            {
                "type": "choose",
                "config": {
                    "prompt": "Category",
                    "items": ["Food", "Gas & Transportation", "Entertainment",
                             "Subscriptions", "Debt Payment", "Other"]
                }
            },
            {
                "type": "ask",
                "config": {
                    "question": "Where? (Optional)",
                    "defaultAnswer": "",
                    "type": "Text"
                }
            },
            {
                "type": "url",
                "config": {
                    "method": "POST",
                    "url": "http://100.68.201.55:8080/finance/expense",
                    "headers": {"Content-Type": "application/json"},
                    "body": {
                        "amount": "${Amount}",
                        "category": "${Category}",
                        "merchant": "${Merchant}",
                        "description": "Logged from iPhone"
                    }
                }
            },
            {
                "type": "notification",
                "config": {
                    "title": "Expense Logged",
                    "body": "Logged ${Amount} in ${Category}. Budget remaining: ${budget_remaining}"
                }
            }
        ]
    }

    # Convert to JSON for display
    config_json = json.dumps(shortcut_config, indent=2)

    # Create HTML page content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Quick Expense Shortcut Setup</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto; }}
        .step {{ margin-bottom: 25px; padding: 15px; background: #f5f5f7; border-radius: 10px; }}
        .step-number {{ display: inline-block; background: #007aff; color: white; width: 24px; height: 24px; border-radius: 12px; text-align: center; line-height: 24px; margin-right: 10px; }}
        code {{ background: #e8e8ed; padding: 2px 6px; border-radius: 4px; font-family: 'Menlo', monospace; }}
        .note {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 15px 0; }}
    </style>
</head>
<body>
    <h1>📱 Quick Expense Shortcut Setup</h1>

    <div class="note">
        <strong>Note:</strong> Scan this QR code on your iPhone, then follow the instructions below to create the shortcut manually.
    </div>

    <div class="step">
        <h3><span class="step-number">1</span> Open Shortcuts App</h3>
        <p>Open the <strong>Shortcuts</strong> app on your iPhone.</p>
    </div>

    <div class="step">
        <h3><span class="step-number">2</span> Create New Shortcut</h3>
        <p>Tap the <strong>+</strong> icon in the top right.</p>
    </div>

    <div class="step">
        <h3><span class="step-number">3</span> Add Actions</h3>
        <p>Add these actions in order:</p>
        <ol>
            <li><strong>Ask for Input</strong> → Question: "Amount?" → Type: Number → Save as: "Amount"</li>
            <li><strong>Choose from Menu</strong> → Options: Food, Gas & Transportation, Entertainment, Subscriptions, Debt Payment, Other → Save selection as: "Category"</li>
            <li><strong>Ask for Input</strong> → Question: "Where? (Optional)" → Type: Text → Save as: "Merchant"</li>
            <li><strong>Get Contents of URL</strong> → URL: <code>http://100.68.201.55:8080/finance/expense</code> → Method: POST → Headers: <code>Content-Type: application/json</code> → Body: JSON (see below)</li>
            <li><strong>Get Dictionary Value</strong> → Key: <code>budget_remaining</code> → From: Contents of URL</li>
            <li><strong>Show Notification</strong> → Title: "Expense Logged" → Body: "Logged $[Amount] in [Category]. Budget remaining: $[Remaining]"</li>
        </ol>

        <p><strong>JSON Body for URL action:</strong></p>
        <pre><code>{{
  "amount": "[Amount]",
  "category": "[Category]",
  "merchant": "[Merchant]",
  "description": "Logged from iPhone"
}}</code></pre>
    </div>

    <div class="step">
        <h3><span class="step-number">4</span> Save Shortcut</h3>
        <p>Tap <strong>Next</strong>, name it "Quick Expense", choose the 💰 icon, and tap <strong>Done</strong>.</p>
    </div>

    <div class="step">
        <h3><span class="step-number">5</span> Test It!</h3>
        <p>Run the shortcut and enter: <code>12.99</code> for amount, choose <code>Food</code> for category.</p>
        <p>You should get a notification confirming the expense was logged.</p>
    </div>

    <div class="note">
        <strong>Server IP:</strong> If your Tailscale IP changes, update the URL in the shortcut to: <code>http://[new-ip]:8080/finance/expense</code>
    </div>

    <p style="text-align: center; margin-top: 30px; color: #666; font-size: 0.9em;">
        Generated by NEXUS • {json.dumps(datetime.now().strftime('%Y-%m-%d'))}
    </p>
</body>
</html>"""

    # Save HTML file
    html_path = Path("docs/shortcut_setup.html")
    html_path.parent.mkdir(exist_ok=True)
    html_path.write_text(html_content)

    # Generate QR code that links to the HTML file
    # For local use, we'll create a QR code with the file path
    # In real use, this would be served over HTTP

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    # QR content: instructions to open the HTML file
    qr_content = """Quick Expense Shortcut Setup

To set up the Quick Expense shortcut on your iPhone:

1. Open Shortcuts app
2. Create new shortcut (+ icon)
3. Add these actions:
   - Ask for Input: "Amount?" (Number)
   - Choose from Menu: Categories
   - Ask for Input: "Where?" (Text, optional)
   - Get Contents of URL:
     URL: http://100.68.201.55:8080/finance/expense
     Method: POST
     Headers: Content-Type: application/json
     Body: {"amount":"[Amount]","category":"[Category]","merchant":"[Merchant]","description":"Logged from iPhone"}
   - Get Dictionary Value: budget_remaining
   - Show Notification: "Logged $[Amount] in [Category]. Budget remaining: $[Remaining]"

See docs/iphone_quick_expense_shortcut.md for detailed instructions.
"""

    qr.add_data(qr_content)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Save image
    qr_path = Path("docs/shortcut_qr.png")
    img.save(qr_path)

    print(f"✅ QR code generated: {qr_path}")
    print(f"✅ HTML instructions: {html_path}")
    print(f"✅ Documentation: docs/iphone_quick_expense_shortcut.md")
    print("\nTo use:")
    print("1. Display the QR code on your computer screen")
    print("2. Scan with iPhone camera")
    print("3. Follow the instructions")

    return qr_path, html_path

if __name__ == "__main__":
    # Check for qrcode library
    try:
        import qrcode
    except ImportError:
        print("Installing qrcode library...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode[pil]"])
        import qrcode

    from datetime import datetime
    generate_qr_code()
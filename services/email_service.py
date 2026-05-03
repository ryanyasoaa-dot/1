import smtplib
import os
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _send(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email. Returns True on success, False on failure."""
    try:
        server   = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        port     = int(os.getenv('SMTP_PORT', 587))
        sender   = os.getenv('EMAIL_ADDRESS', '')
        password = os.getenv('EMAIL_PASSWORD', '')
        use_tls  = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'Grande Marketplace <{sender}>'
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(server, port) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(sender, password)
            smtp.sendmail(sender, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'[EmailService] Failed to send to {to_email}: {e}')
        return False


def send_order_confirmation(to_email: str, buyer_name: str, order: dict, items: list) -> bool:
    """Send order confirmation email to buyer after checkout."""
    order_id      = (order.get('id') or '')[:8].upper()
    total         = float(order.get('total_amount', 0))
    payment       = (order.get('payment_method') or 'cod').replace('_', ' ').title()
    address       = order.get('shipping_address') or {}
    address_str   = ', '.join(filter(None, [
        address.get('street'), address.get('barangay'),
        address.get('city'),   address.get('region')
    ]))

    rows = ''
    for item in items:
        product = item.get('product') or {}
        name    = product.get('name', 'Product')
        qty     = item.get('quantity', 1)
        price   = float(item.get('unit_price', 0))
        rows += f'''
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">{name}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:center">{qty}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:right">&#8369;{price:,.2f}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:right">&#8369;{price * qty:,.2f}</td>
        </tr>'''

    html = f'''
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f4f4f8;font-family:Inter,Arial,sans-serif">
    <div style="max-width:600px;margin:32px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08)">

      <!-- Header -->
      <div style="background:linear-gradient(135deg,#FF2BAC,#FF6BCE);padding:32px 40px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:28px;font-weight:700;letter-spacing:-0.5px">Grande</h1>
        <p style="color:rgba(255,255,255,.85);margin:6px 0 0;font-size:14px">Order Confirmation</p>
      </div>

      <!-- Body -->
      <div style="padding:32px 40px">
        <p style="font-size:16px;color:#1a1a3e;margin:0 0 8px">Hi <strong>{buyer_name}</strong>,</p>
        <p style="font-size:14px;color:#6c757d;margin:0 0 24px">
          Thank you for your order! We've received it and it's now being reviewed by the seller.
        </p>

        <!-- Order Info -->
        <div style="background:#f8f9fa;border-radius:10px;padding:16px 20px;margin-bottom:24px">
          <table style="width:100%;border-collapse:collapse">
            <tr>
              <td style="font-size:13px;color:#6c757d;padding:4px 0">Order ID</td>
              <td style="font-size:13px;font-weight:600;color:#1a1a3e;text-align:right">#{order_id}</td>
            </tr>
            <tr>
              <td style="font-size:13px;color:#6c757d;padding:4px 0">Payment</td>
              <td style="font-size:13px;font-weight:600;color:#1a1a3e;text-align:right">{payment}</td>
            </tr>
            <tr>
              <td style="font-size:13px;color:#6c757d;padding:4px 0">Deliver to</td>
              <td style="font-size:13px;font-weight:600;color:#1a1a3e;text-align:right">{address_str or 'See account'}</td>
            </tr>
          </table>
        </div>

        <!-- Items Table -->
        <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
          <thead>
            <tr style="background:#f8f9fa">
              <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6c757d;font-weight:600;text-transform:uppercase">Item</th>
              <th style="padding:10px 12px;text-align:center;font-size:12px;color:#6c757d;font-weight:600;text-transform:uppercase">Qty</th>
              <th style="padding:10px 12px;text-align:right;font-size:12px;color:#6c757d;font-weight:600;text-transform:uppercase">Price</th>
              <th style="padding:10px 12px;text-align:right;font-size:12px;color:#6c757d;font-weight:600;text-transform:uppercase">Subtotal</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
          <tfoot>
            <tr>
              <td colspan="3" style="padding:12px;text-align:right;font-weight:700;font-size:15px;color:#1a1a3e">Total</td>
              <td style="padding:12px;text-align:right;font-weight:700;font-size:15px;color:#FF2BAC">&#8369;{total:,.2f}</td>
            </tr>
          </tfoot>
        </table>

        <p style="font-size:13px;color:#6c757d;margin:0">
          You can track your order status anytime from your
          <a href="#" style="color:#FF2BAC;text-decoration:none;font-weight:600">Orders page</a>.
        </p>
      </div>

      <!-- Footer -->
      <div style="background:#f8f9fa;padding:20px 40px;text-align:center;border-top:1px solid #f0f0f0">
        <p style="font-size:12px;color:#adb5bd;margin:0">
          &copy; 2025 Grande Marketplace &mdash; This is an automated email, please do not reply.
        </p>
      </div>
    </div>
    </body>
    </html>'''

    return _send(to_email, f'Order Confirmed #{order_id} — Grande', html)


def send_password_reset(to_email: str, name: str, reset_url: str) -> bool:
    """Send password reset link email."""
    html = f'''
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f4f4f8;font-family:Inter,Arial,sans-serif">
    <div style="max-width:520px;margin:32px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08)">

      <div style="background:linear-gradient(135deg,#FF2BAC,#FF6BCE);padding:32px 40px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:28px;font-weight:700">Grande</h1>
        <p style="color:rgba(255,255,255,.85);margin:6px 0 0;font-size:14px">Password Reset</p>
      </div>

      <div style="padding:32px 40px">
        <p style="font-size:16px;color:#1a1a3e;margin:0 0 8px">Hi <strong>{name}</strong>,</p>
        <p style="font-size:14px;color:#6c757d;margin:0 0 28px">
          We received a request to reset your password. Click the button below to set a new one.
          This link expires in <strong>1 hour</strong>.
        </p>

        <div style="text-align:center;margin-bottom:28px">
          <a href="{reset_url}"
             style="display:inline-block;background:linear-gradient(135deg,#FF2BAC,#FF6BCE);
                    color:#fff;text-decoration:none;padding:14px 36px;border-radius:10px;
                    font-size:15px;font-weight:700;letter-spacing:.3px">
            Reset My Password
          </a>
        </div>

        <p style="font-size:12px;color:#adb5bd;margin:0">
          If you didn't request this, you can safely ignore this email. Your password won't change.
        </p>
      </div>

      <div style="background:#f8f9fa;padding:20px 40px;text-align:center;border-top:1px solid #f0f0f0">
        <p style="font-size:12px;color:#adb5bd;margin:0">
          &copy; 2025 Grande Marketplace &mdash; This is an automated email, please do not reply.
        </p>
      </div>
    </div>
    </body>
    </html>'''

    return _send(to_email, 'Reset Your Password — Grande', html)


def send_otp_email(to_email: str, name: str, otp: str) -> bool:
    """Send OTP verification email."""
    html = f'''
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f4f4f8;font-family:Inter,Arial,sans-serif">
    <div style="max-width:520px;margin:32px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08)">

      <div style="background:linear-gradient(135deg,#FF2BAC,#FF6BCE);padding:32px 40px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:28px;font-weight:700">Grande</h1>
        <p style="color:rgba(255,255,255,.85);margin:6px 0 0;font-size:14px">Email Verification</p>
      </div>

      <div style="padding:32px 40px">
        <p style="font-size:16px;color:#1a1a3e;margin:0 0 8px">Hi <strong>{name}</strong>,</p>
        <p style="font-size:14px;color:#6c757d;margin:0 0 28px">
          Thank you for registering! Please verify your email address by entering the code below.
          This code expires in <strong>10 minutes</strong>.
        </p>

        <div style="text-align:center;margin-bottom:28px">
          <div style="display:inline-block;background:#f8f9fa;border:2px dashed #FF2BAC;border-radius:12px;padding:20px 40px">
            <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:#FF2BAC;font-family:monospace">{otp}</span>
          </div>
        </div>

        <p style="font-size:12px;color:#adb5bd;margin:0">
          If you didn't request this, you can safely ignore this email.
        </p>
      </div>

      <div style="background:#f8f9fa;padding:20px 40px;text-align:center;border-top:1px solid #f0f0f0">
        <p style="font-size:12px;color:#adb5bd;margin:0">
          &copy; 2025 Grande Marketplace &mdash; This is an automated email, please do not reply.
        </p>
      </div>
    </div>
    </body>
    </html>'''

    return _send(to_email, 'Your Verification Code — Grande', html)

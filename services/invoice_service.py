from flask import render_template
from datetime import datetime

def generate_invoice_html(item, item_type='service'):
    """
    Renders clean, printable invoice HTML for either a Service Request or an Order.
    """
    invoice_data = {
        'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'item_type': item_type,
        'item': item
    }
    return render_template('invoice.html', **invoice_data)

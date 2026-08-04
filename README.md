# MotoServe 360

Integrated Fuel Delivery, Vehicle Repair, Towing and Vehicle Products Management System built with **Python 3.12, Flask, SQLAlchemy, Bootstrap 5, Leaflet JS, and Chart.js**.

---

## 🌟 Features Overview

### 1. 👤 Customer Panel
- **Registration & Authentication**: Separate login/register flow.
- **Vehicle Management**: Register and manage multiple cars, motorcycles, or commercial vehicles with plate numbers and fuel types.
- **On-Demand Fuel Delivery**: Request Petrol, Diesel, or CNG with location pin on Leaflet map, real-time fee calculation, and emergency surge option.
- **On-Site Mechanic Repair**: Request mechanics for engine breakdown, flat tyre, dead battery jumpstart, brake failure, or electrical issues with photo uploads.
- **Emergency Towing Service**: Flatbed and wheel-lift towing with pickup/drop destination distance & fee estimator.
- **🚨 SOS Panic Button**: One-touch emergency broadcast alerting nearest available providers.
- **Auto Products Store**: E-Commerce catalog for lubricants, batteries, tyres, helmets, brake pads, and detailing kits with cart, checkout & payment processing (UPI, Card, Wallet, COD).
- **Live Map Tracking**: Real-time Leaflet OSM tracking of assigned provider location and job progress status (`Accepted` ➔ `Travelling` ➔ `Reached` ➔ `Working` ➔ `Completed`).
- **In-App AJAX Chat**: Direct live communication with assigned service providers.
- **Printable Tax Invoices**: Downloadable HTML/PDF receipts for services & e-commerce orders.
- **Ratings & Reviews**: 5-star rating system with comments for service providers.

### 2. 🛠️ Service Provider Panel
- **Provider Types**: Fuel Delivery Agent, Mechanic, Tow Driver.
- **Registration & Verification**: Document upload (business license/ID) requiring admin approval.
- **Online / Offline Toggle**: Change availability status in real time.
- **Job Console & Status Progression**: Accept/Reject incoming jobs, update progress through 5 workflow states, view navigation map & call customer directly.
- **Earnings & Reviews**: Detailed daily, monthly, and lifetime payout breakdowns with customer feedback scores.

### 3. 🛡️ Admin Panel
- **Executive Analytics Dashboard**: Chart.js visualizations for monthly revenue growth and service breakdown distribution.
- **Provider Approval System**: Approve, Reject, or Suspend service provider applications with document inspection.
- **User Management**: Oversee customer and provider accounts with activate/deactivate toggles.
- **Product Store & Inventory Control**: Add, edit, soft-delete products, adjust stock quantities and percentage discounts.
- **Orders & Service Request Oversight**: Manage status for all fuel, repair, tow requests, and e-commerce orders.
- **System Audit Logs & DB Backup**: Generate instant downloadable SQLite database backups and view administrator action logs.

---

## ⚙️ Installation & Running Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database & Seed Demo Data
```bash
python seed.py
```

### 3. Run the Application
```bash
python app.py
```
Open your browser and navigate to: `http://127.0.0.1:5000`

---

## 🔑 Pre-Configured Demo Login Accounts

| Role | Email | Password | Access Rights |
|---|---|---|---|
| **Admin** | `admin@motoserve360.com` | `admin123` | Full System & Analytics Control |
| **Customer** | `alex@example.com` | `customer123` | Bookings, E-Commerce, Tracking |
| **Fuel Agent** | `fuel_express@motoserve.com` | `provider123` | Fuel Delivery Requests |
| **Mechanic** | `quick_mechanic@motoserve.com` | `provider123` | On-Site Repair Requests |
| **Tow Driver** | `titan_tow@motoserve.com` | `provider123` | Emergency Towing Requests |
| **Pending Provider** | `pending_mechanic@motoserve.com` | `provider123` | For Admin Approval Testing |

---

## 📁 Project Structure

```text
MotoServe360/
├── app.py                      # Flask Application Factory
├── config.py                   # App Configuration & SQLite Paths
├── requirements.txt            # Package Dependencies
├── seed.py                     # Rich Demo Database Seeder
├── README.md                   # Application Documentation
├── instance/
│   └── database.db             # SQLite Database
├── models/                     # SQLAlchemy Database Models
│   ├── __init__.py
│   ├── user.py                 # User & ProviderProfile
│   ├── vehicle.py              # Customer Vehicles
│   ├── service.py              # ServiceRequests, Fuel, Repair, Tow Details
│   ├── product.py              # Products, CartItem, Order, OrderItem
│   ├── payment.py              # Payments
│   ├── communication.py        # Notifications & Chat Messages
│   ├── review.py               # Provider Reviews
│   └── admin_log.py            # Admin Audit Trail Logs
├── services/                   # Business Logic & Algorithms
│   ├── location_service.py     # Haversine Distance & Provider Finding
│   ├── notification_service.py # System Notifications Helper
│   └── invoice_service.py      # Printable Receipt Generator
├── routes/                     # Flask Blueprints
│   ├── main.py                 # Landing Page & Public Sections
│   ├── auth.py                 # Registration & Login Controllers
│   ├── customer.py             # Customer Panel Routes & Store
│   ├── provider.py             # Provider Job Console & Earnings
│   └── admin.py                # Admin Analytics & Approvals
├── static/
│   ├── css/                    # Custom CSS & Glassmorphism Styling
│   ├── js/                     # Leaflet Maps, AJAX Chat, Chart.js Visualizers
│   └── uploads/                # Provider Verification Documents & Images
└── templates/                  # Modular HTML5 Templates
    ├── base.html
    ├── index.html
    ├── invoice.html
    ├── auth/
    ├── customer/
    ├── provider/
    └── admin/
```

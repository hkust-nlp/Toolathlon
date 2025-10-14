import json
import random
import datetime
import csv
import pandas as pd
from typing import Dict, List, Any
import uuid
from dataclasses import dataclass, asdict
import os
import argparse

@dataclass
class TransactionRecord:
    transaction_id: str
    user_id: str
    account_id: str
    merchant_id: str
    card_id: str
    device_id: str
    amount: float
    currency: str
    transaction_type: str
    status: str
    timestamp: str
    location_id: str
    risk_score: float
    flags: List[str]

class LiveTransactionsDataGenerator:
    def __init__(self, scale_factor: int = 1, suspicious_transactions_count: int = 1):
        """
        Initialize the data generator.
        
        Args:
            scale_factor: Data scale factor (1=base, 2=double base, etc.)
            suspicious_transactions_count: Number of suspicious transactions
        """
        self.scale_factor = scale_factor
        self.suspicious_transactions_count = suspicious_transactions_count
        
        # Base configuration
        self.base_counts = {
            'normal_users': 5,
            'normal_transactions': 20,
            'normal_merchants': 5,
            'related_transactions_per_suspicious': 4
        }
        
        # Actual number calculation
        self.actual_counts = {
            'normal_users': self.base_counts['normal_users'] * scale_factor,
            'normal_transactions': self.base_counts['normal_transactions'] * scale_factor,
            'normal_merchants': self.base_counts['normal_merchants'] * scale_factor,
            'related_transactions_per_suspicious': self.base_counts['related_transactions_per_suspicious']
        }
        
        # Suspicious transaction IDs
        self.suspicious_transaction_ids = [f"T8492XJ{i}" for i in range(1, suspicious_transactions_count + 1)]
        self.main_suspicious_id = "T8492XJ3" if "T8492XJ3" in self.suspicious_transaction_ids else self.suspicious_transaction_ids[0]
        
        # Suspicious IDs (each suspicious tx has corresponding entities)
        self.suspicious_user_ids = [f"U{8847291 + i}" for i in range(suspicious_transactions_count)]
        self.suspicious_account_ids = [f"AC{7739284 + i}" for i in range(suspicious_transactions_count)]
        self.suspicious_merchant_ids = [f"MER{9934812 + i}" for i in range(suspicious_transactions_count)]
        self.suspicious_card_ids = [f"CARD{6672839 + i}" for i in range(suspicious_transactions_count)]
        self.suspicious_device_ids = [f"DEV{4482913 + i}" for i in range(suspicious_transactions_count)]
        
        # Location data
        self.locations = {
            "LOC001": {"city": "New York", "country": "USA", "latitude": 40.7128, "longitude": -74.0060, "timezone": "America/New_York"},
            "LOC002": {"city": "London", "country": "UK", "latitude": 51.5074, "longitude": -0.1278, "timezone": "Europe/London"},
            "LOC003": {"city": "Tokyo", "country": "Japan", "latitude": 35.6762, "longitude": 139.6503, "timezone": "Asia/Tokyo"},
            "LOC004": {"city": "Moscow", "country": "Russia", "latitude": 55.7558, "longitude": 37.6176, "timezone": "Europe/Moscow"},
            "LOC005": {"city": "Lagos", "country": "Nigeria", "latitude": 6.5244, "longitude": 3.3792, "timezone": "Africa/Lagos"},
            "LOC006": {"city": "Hong Kong", "country": "Hong Kong", "latitude": 22.3193, "longitude": 114.1694, "timezone": "Asia/Hong_Kong"},
            "LOC007": {"city": "Dubai", "country": "UAE", "latitude": 25.2048, "longitude": 55.2708, "timezone": "Asia/Dubai"},
            "LOC008": {"city": "Singapore", "country": "Singapore", "latitude": 1.3521, "longitude": 103.8198, "timezone": "Asia/Singapore"},
            "LOC009": {"city": "Frankfurt", "country": "Germany", "latitude": 50.1109, "longitude": 8.6821, "timezone": "Europe/Berlin"},
            "LOC010": {"city": "Sydney", "country": "Australia", "latitude": -33.8688, "longitude": 151.2093, "timezone": "Australia/Sydney"}
        }
        
    def generate_users(self) -> List[Dict[str, Any]]:
        """Generate user data"""
        users = []
        
        # Suspicious users
        for i, user_id in enumerate(self.suspicious_user_ids):
            users.append({
                "user_id": user_id,
                "username": f"alex_chen_{88 + i}",
                "email": f"alex.chen.crypto{i}@protonmail.com",
                "phone": f"+1-555-847-{9284 + i}",
                "first_name": "Alex",
                "last_name": f"Chen{i if i > 0 else ''}",
                "date_of_birth": f"{1988 + i % 5}-03-15",
                "nationality": "USA",
                "registration_date": f"2023-02-{14 + i % 14:02d}",
                "kyc_status": "VERIFIED",
                "risk_level": "HIGH",
                "last_login": f"2024-01-15T23:{47 - i % 10:02d}:12Z",
                "login_count_30d": 847 + i * 50,
                "failed_login_attempts": 12 + i,
                "account_locked": False,
                "suspicious_activity_score": round(8.7 + i * 0.1, 1)
            })
        
        # Normal users
        base_users = [
            {"username": "john_smith", "email": "john.smith@gmail.com", "risk_level": "LOW"},
            {"username": "mary_jones", "email": "mary.jones@outlook.com", "risk_level": "MEDIUM"},
            {"username": "david_wilson", "email": "david.wilson@yahoo.com", "risk_level": "LOW"},
            {"username": "sarah_davis", "email": "sarah.davis@hotmail.com", "risk_level": "LOW"},
            {"username": "mike_brown", "email": "mike.brown@icloud.com", "risk_level": "MEDIUM"}
        ]
        
        for i in range(self.actual_counts['normal_users']):
            base_user = base_users[i % len(base_users)]
            user_id = f"U{1001234 + i}"
            username = f"{base_user['username']}_{i}" if i >= len(base_users) else base_user['username']
            
            users.append({
                "user_id": user_id,
                "username": username,
                "email": f"{username.replace('_', '.')}@gmail.com",
                "phone": f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
                "first_name": username.split("_")[0].title(),
                "last_name": username.split("_")[1].title() if "_" in username else "User",
                "date_of_birth": f"{random.randint(1980,2000)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "nationality": "USA",
                "registration_date": f"2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "kyc_status": "VERIFIED",
                "risk_level": base_user["risk_level"],
                "last_login": f"2024-01-{random.randint(10,15):02d}T{random.randint(8,20):02d}:{random.randint(0,59):02d}:00Z",
                "login_count_30d": random.randint(10, 50),
                "failed_login_attempts": random.randint(0, 3),
                "account_locked": False,
                "suspicious_activity_score": round(random.uniform(0.1, 3.0), 1)
            })
            
        return users
    
    def generate_accounts(self) -> List[Dict[str, Any]]:
        """Generate account data"""
        accounts = []
        
        # Suspicious accounts
        for i, account_id in enumerate(self.suspicious_account_ids):
            accounts.append({
                "account_id": account_id,
                "user_id": self.suspicious_user_ids[i],
                "account_type": "CRYPTO_TRADING",
                "account_status": "ACTIVE",
                "balance_usd": round(2847392.85 + i * 100000, 2),
                "balance_btc": round(47.28394 + i * 5.5, 5),
                "balance_eth": round(892.7394 + i * 50.3, 4),
                "daily_limit": 500000.00,
                "monthly_limit": 5000000.00,
                "created_date": f"2023-02-{14 + i % 14:02d}",
                "last_transaction": f"2024-01-15T23:{47 - i % 10:02d}:12Z",
                "transaction_count_30d": 1247 + i * 100,
                "volume_30d_usd": round(8947293.74 + i * 500000, 2),
                "high_risk_transactions_30d": 23 + i * 5,
                "frozen": False,
                "investigation_notes": f"Multiple large volume transactions, pattern analysis required - Account {i+1}"
            })
        
        # Normal accounts
        account_types = ["CHECKING", "SAVINGS", "INVESTMENT", "BUSINESS"]
        for i in range(self.actual_counts['normal_users']):
            account_id = f"AC{1000000 + i}"
            user_id = f"U{1001234 + i}"
            
            accounts.append({
                "account_id": account_id,
                "user_id": user_id,
                "account_type": account_types[i % len(account_types)],
                "account_status": "ACTIVE",
                "balance_usd": round(random.uniform(1000, 50000), 2),
                "daily_limit": 10000.00,
                "monthly_limit": 50000.00,
                "created_date": f"2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "last_transaction": f"2024-01-{random.randint(10,15):02d}T{random.randint(8,20):02d}:00:00Z",
                "transaction_count_30d": random.randint(5, 30),
                "volume_30d_usd": round(random.uniform(1000, 15000), 2),
                "high_risk_transactions_30d": 0,
                "frozen": False,
                "investigation_notes": None
            })
            
        return accounts
    
    def generate_merchants(self) -> List[Dict[str, Any]]:
        """Generate merchant data"""
        merchants = []
        
        # Suspicious merchants
        suspicious_merchant_names = [
            "Global Digital Assets Exchange",
            "Crypto Freedom Trading",
            "Anonymous Coin Exchange",
            "Dark Web Crypto Hub",
            "Offshore Digital Markets"
        ]
        
        for i, merchant_id in enumerate(self.suspicious_merchant_ids):
            name = suspicious_merchant_names[i % len(suspicious_merchant_names)]
            merchants.append({
                "merchant_id": merchant_id,
                "business_name": f"{name} {i+1}" if i > 0 else name,
                "legal_name": f"GDAE Holdings Ltd {i+1}" if i > 0 else "GDAE Holdings Ltd",
                "merchant_category": "CRYPTOCURRENCY_EXCHANGE",
                "country": ["Russia", "Estonia", "Cyprus", "Malta"][i % 4],
                "registration_number": f"RU{847392847 + i}",
                "license_status": "SUSPENDED",
                "risk_rating": "VERY_HIGH",
                "kyb_status": "UNDER_REVIEW",
                "processing_volume_30d": round(94739283.74 + i * 10000000, 2),
                "transaction_count_30d": 8372 + i * 500,
                "chargeback_rate": round(12.4 + i * 0.5, 1),
                "fraud_reports": 23 + i * 3,
                "compliance_score": round(2.1 + i * 0.1, 1),
                "last_audit_date": f"2023-11-{15 + i % 15:02d}",
                "sanctions_check": "FLAGGED",
                "shell_company_indicators": ["offshore_jurisdiction", "recent_incorporation", "minimal_physical_presence"],
                "beneficial_owners": [
                    {"name": f"Viktor Petrov {i+1}" if i > 0 else "Viktor Petrov", "nationality": "Russia", "ownership_pct": 45.2},
                    {"name": f"Anonymous Trust Fund {i+1}" if i > 0 else "Anonymous Trust Fund", "nationality": "Cyprus", "ownership_pct": 54.8}
                ]
            })
        
        # Normal merchants
        normal_merchant_names = [
            {"name": "Amazon.com", "category": "ECOMMERCE", "risk": "LOW"},
            {"name": "Starbucks Corp", "category": "RESTAURANTS", "risk": "LOW"},
            {"name": "Shell Gas Station", "category": "GAS_STATIONS", "risk": "LOW"},
            {"name": "Apple Store", "category": "ELECTRONICS", "risk": "LOW"},
            {"name": "Target Corporation", "category": "RETAIL", "risk": "LOW"},
            {"name": "Walmart Inc", "category": "RETAIL", "risk": "LOW"},
            {"name": "McDonald's", "category": "RESTAURANTS", "risk": "LOW"},
            {"name": "Home Depot", "category": "HOME_IMPROVEMENT", "risk": "LOW"},
            {"name": "Best Buy", "category": "ELECTRONICS", "risk": "LOW"},
            {"name": "Costco Wholesale", "category": "WHOLESALE", "risk": "LOW"}
        ]
        
        for i in range(self.actual_counts['normal_merchants']):
            base_merchant = normal_merchant_names[i % len(normal_merchant_names)]
            merchant_id = f"MER{100000 + i}"
            
            merchants.append({
                "merchant_id": merchant_id,
                "business_name": f"{base_merchant['name']} {i+1}" if i >= len(normal_merchant_names) else base_merchant['name'],
                "legal_name": f"{base_merchant['name']} {i+1}" if i >= len(normal_merchant_names) else base_merchant['name'],
                "merchant_category": base_merchant["category"],
                "country": "USA",
                "registration_number": f"US{random.randint(100000000, 999999999)}",
                "license_status": "ACTIVE",
                "risk_rating": base_merchant["risk"],
                "kyb_status": "VERIFIED",
                "processing_volume_30d": round(random.uniform(100000, 1000000), 2),
                "transaction_count_30d": random.randint(1000, 5000),
                "chargeback_rate": round(random.uniform(0.1, 2.0), 1),
                "fraud_reports": random.randint(0, 2),
                "compliance_score": round(random.uniform(8.0, 9.5), 1),
                "last_audit_date": "2023-12-01",
                "sanctions_check": "CLEAN",
                "shell_company_indicators": [],
                "beneficial_owners": []
            })
            
        return merchants
    
    def generate_cards(self) -> List[Dict[str, Any]]:
        """Generate card data"""
        cards = []
        
        # Suspicious cards
        for i, card_id in enumerate(self.suspicious_card_ids):
            cards.append({
                "card_id": card_id,
                "user_id": self.suspicious_user_ids[i],
                "card_number_masked": f"5547-****-****-{2839 + i}",
                "card_type": "PREPAID",
                "issuer": f"Crypto Card International {i+1}" if i > 0 else "Crypto Card International",
                "issuer_country": ["Estonia", "Cyprus", "Malta", "Latvia"][i % 4],
                "expiry_date": f"202{5 + i % 5}-12",
                "status": "ACTIVE",
                "created_date": f"2024-01-{2 + i % 28:02d}",
                "last_used": f"2024-01-15T23:{47 - i % 10:02d}:12Z",
                "transaction_count_30d": 847 + i * 50,
                "volume_30d": round(2847392.85 + i * 100000, 2),
                "velocity_flags": ["HIGH_FREQUENCY", "LARGE_AMOUNTS", "CROSS_BORDER"],
                "card_present_rate": round(5.2 + i * 0.5, 1),
                "online_transaction_rate": round(94.8 - i * 0.5, 1),
                "foreign_transaction_rate": round(78.4 + i * 2, 1),
                "atm_withdrawal_count_30d": 2 + i,
                "pos_transaction_count_30d": 12 + i * 3,
                "ecommerce_transaction_count_30d": 833 + i * 40
            })
        
        # Normal cards
        normal_card_types = [
            {"type": "CREDIT", "issuer": "Chase", "prefix": "4532"},
            {"type": "DEBIT", "issuer": "Bank of America", "prefix": "4716"},
            {"type": "CREDIT", "issuer": "Capital One", "prefix": "5425"},
            {"type": "DEBIT", "issuer": "Wells Fargo", "prefix": "4111"},
            {"type": "CREDIT", "issuer": "Citibank", "prefix": "5555"}
        ]
        
        for i in range(self.actual_counts['normal_users']):
            card_type = normal_card_types[i % len(normal_card_types)]
            card_id = f"CARD{100000 + i}"
            user_id = f"U{1001234 + i}"
            
            cards.append({
                "card_id": card_id,
                "user_id": user_id,
                "card_number_masked": f"{card_type['prefix']}-****-****-{1234 + i}",
                "card_type": card_type["type"],
                "issuer": card_type["issuer"],
                "issuer_country": "USA",
                "expiry_date": f"202{random.randint(5,9)}-{random.randint(1,12):02d}",
                "status": "ACTIVE",
                "created_date": f"2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "last_used": f"2024-01-{random.randint(10,15):02d}T{random.randint(8,20):02d}:00:00Z",
                "transaction_count_30d": random.randint(10, 50),
                "volume_30d": round(random.uniform(1000, 15000), 2),
                "velocity_flags": [],
                "card_present_rate": round(random.uniform(60, 80), 1),
                "online_transaction_rate": round(random.uniform(20, 40), 1),
                "foreign_transaction_rate": round(random.uniform(0, 10), 1),
                "atm_withdrawal_count_30d": random.randint(2, 8),
                "pos_transaction_count_30d": random.randint(15, 35),
                "ecommerce_transaction_count_30d": random.randint(5, 15)
            })
            
        return cards
    
    def generate_devices(self) -> List[Dict[str, Any]]:
        """Generate device data"""
        devices = []
        
        # Suspicious devices
        suspicious_ips = [
            "185.220.101.47",  # Tor exit node
            "192.42.116.173",  # Another Tor exit
            "199.87.154.255",  # VPN exit
            "103.251.167.20"   # Suspicious VPN
        ]
        
        for i, device_id in enumerate(self.suspicious_device_ids):
            devices.append({
                "device_id": device_id,
                "user_id": self.suspicious_user_ids[i],
                "device_fingerprint": f"def{456789 + i}abcdef{123456789 + i}abcdef{12 + i}",
                "device_type": "MOBILE",
                "os": f"Android {14 + i % 3}",
                "browser": f"Chrome Mobile {121 + i}.0",
                "ip_address": suspicious_ips[i % len(suspicious_ips)],
                "country": ["Russia", "Estonia", "Cyprus", "Latvia"][i % 4],
                "city": ["Moscow", "Tallinn", "Nicosia", "Riga"][i % 4],
                "isp": f"Unknown VPN Service {i+1}" if i > 0 else "Unknown VPN Service",
                "proxy_detected": True,
                "tor_detected": True,
                "vpn_detected": True,
                "first_seen": f"2024-01-15T23:{30 + i % 15:02d}:00Z",
                "last_seen": f"2024-01-15T23:{47 - i % 10:02d}:12Z",
                "session_count": 1 + i,
                "is_trusted": False,
                "risk_score": round(9.8 - i * 0.1, 1),
                "geolocation_spoofing": True,
                "device_id_spoofing": True,
                "multiple_users_detected": False,
                "suspicious_user_agent": True,
                "screen_resolution": "unknown",
                "timezone": ["Europe/Moscow", "Europe/Tallinn", "Asia/Nicosia", "Europe/Riga"][i % 4],
                "language": "en-US"
            })
        
        # Normal devices
        normal_devices = [
            {"os": "iOS 17.2", "browser": "Safari", "country": "USA"},
            {"os": "Windows 11", "browser": "Edge", "country": "USA"},
            {"os": "macOS 14", "browser": "Chrome", "country": "USA"},
            {"os": "Android 13", "browser": "Chrome Mobile", "country": "USA"},
            {"os": "iOS 16.5", "browser": "Safari", "country": "USA"}
        ]
        
        for i in range(self.actual_counts['normal_users']):
            device = normal_devices[i % len(normal_devices)]
            device_id = f"DEV{100000 + i}"
            user_id = f"U{1001234 + i}"
            
            devices.append({
                "device_id": device_id,
                "user_id": user_id,
                "device_fingerprint": f"abc{random.randint(100000000, 999999999)}def{random.randint(100000000, 999999999)}",
                "device_type": "MOBILE" if "iOS" in device["os"] or "Android" in device["os"] else "DESKTOP",
                "os": device["os"],
                "browser": device["browser"],
                "ip_address": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                "country": device["country"],
                "city": "New York",
                "isp": "Verizon Communications",
                "proxy_detected": False,
                "tor_detected": False,
                "vpn_detected": False,
                "first_seen": f"2023-{random.randint(1,12):02d}-{random.randint(1,28):02d}T00:00:00Z",
                "last_seen": f"2024-01-{random.randint(10,15):02d}T{random.randint(8,20):02d}:00:00Z",
                "session_count": random.randint(50, 200),
                "is_trusted": True,
                "risk_score": round(random.uniform(0.1, 2.0), 1),
                "geolocation_spoofing": False,
                "device_id_spoofing": False,
                "multiple_users_detected": False,
                "suspicious_user_agent": False,
                "screen_resolution": "1920x1080",
                "timezone": "America/New_York",
                "language": "en-US"
            })
            
        return devices
    
    def generate_live_transactions(self) -> List[Dict[str, Any]]:
        """Generate live transactions data"""
        transactions = []
        
        # Suspicious transactions
        for i, tx_id in enumerate(self.suspicious_transaction_ids):
            amount = 487392.85 + i * 50000
            btc_amount = 15.247 + i * 1.5
            
            transactions.append({
                "transaction_id": tx_id,
                "user_id": self.suspicious_user_ids[i],
                "account_id": self.suspicious_account_ids[i],
                "merchant_id": self.suspicious_merchant_ids[i],
                "card_id": self.suspicious_card_ids[i],
                "device_id": self.suspicious_device_ids[i],
                "amount": round(amount, 2),
                "currency": "USD",
                "original_amount": round(btc_amount, 6),
                "original_currency": "BTC",
                "exchange_rate": round(amount / btc_amount, 2),
                "transaction_type": "CRYPTO_EXCHANGE",
                "sub_type": "BTC_TO_USD",
                "status": "COMPLETED",
                "timestamp": f"2024-01-15T23:{47 - i % 10:02d}:12Z",
                "location_id": f"LOC{4 + i % 4:03d}",
                "processing_time_ms": 234 + i * 10,
                "risk_score": round(9.6 - i * 0.1, 1),
                "ml_fraud_score": round(94.7 - i * 0.5, 1),
                "rule_based_score": round(8.8 + i * 0.1, 1),
                "behavioral_score": round(9.9 - i * 0.1, 1),
                "flags": [
                    "LARGE_AMOUNT",
                    "UNUSUAL_TIME",
                    "NEW_DEVICE", 
                    "VPN_DETECTED",
                    "HIGH_RISK_MERCHANT",
                    "VELOCITY_EXCEEDED",
                    "GEOGRAPHIC_MISMATCH",
                    "SUSPICIOUS_PATTERN"
                ],
                "velocity_checks": {
                    "transactions_last_hour": 15 + i * 2,
                    "amount_last_hour": round(847392.85 + i * 100000, 2),
                    "transactions_last_day": 87 + i * 10,
                    "amount_last_day": round(2847392.85 + i * 500000, 2),
                    "different_merchants_last_day": 12 + i
                },
                "geographic_data": {
                    "user_home_country": "USA",
                    "transaction_country": ["Russia", "Estonia", "Cyprus", "Latvia"][i % 4],
                    "distance_from_home_km": 7844 + i * 100,
                    "unusual_location": True,
                    "travel_time_feasible": False
                },
                "device_analysis": {
                    "new_device": True,
                    "device_reputation": "HIGH_RISK",
                    "proxy_score": round(10.0 - i * 0.1, 1),
                    "device_fingerprint_match": False
                },
                "merchant_analysis": {
                    "merchant_risk_level": "VERY_HIGH",
                    "license_suspended": True,
                    "sanctions_flagged": True,
                    "first_transaction_with_merchant": i == 0,
                    "merchant_volume_spike": True
                },
                "network_analysis": {
                    "connected_suspicious_users": 3 + i,
                    "shared_device_indicators": 2 + i,
                    "money_laundering_pattern_score": round(8.9 + i * 0.1, 1)
                }
            })
            
            # Related test transactions for each suspicious transaction
            for j in range(self.actual_counts['related_transactions_per_suspicious']):
                related_tx_id = f"T8492XJ{1 + i}-{j + 1}"
                test_amount = [1.00, 5.00, 12847.33, 28473.92][j % 4]
                
                transactions.append({
                    "transaction_id": related_tx_id,
                    "user_id": self.suspicious_user_ids[i],
                    "account_id": self.suspicious_account_ids[i],
                    "merchant_id": self.suspicious_merchant_ids[i],
                    "card_id": self.suspicious_card_ids[i],
                    "device_id": self.suspicious_device_ids[i],
                    "amount": test_amount,
                    "currency": "USD",
                    "transaction_type": "CRYPTO_EXCHANGE",
                    "sub_type": "BTC_TO_USD",
                    "status": "COMPLETED",
                    "timestamp": f"2024-01-15T{23 - j:02d}:{30 + j * 5:02d}:{45 - j * 10:02d}Z",
                    "location_id": f"LOC{4 + i % 4:03d}",
                    "risk_score": round(random.uniform(6.0, 8.5), 1),
                    "flags": [["SMALL_TEST_AMOUNT", "NEW_DEVICE"], 
                             ["SMALL_TEST_AMOUNT", "VELOCITY_PATTERN"],
                             ["VELOCITY_EXCEEDED", "HIGH_RISK_MERCHANT"],
                             ["LARGE_AMOUNT", "GEOGRAPHIC_MISMATCH"]][j % 4]
                })
        
        # Normal transactions
        transaction_types = ["PURCHASE", "WITHDRAWAL", "TRANSFER", "PAYMENT", "REFUND"]
        
        for i in range(self.actual_counts['normal_transactions']):
            tx_id = f"T{random.randint(1000000, 9999999)}"
            user_idx = i % self.actual_counts['normal_users']
            
            transactions.append({
                "transaction_id": tx_id,
                "user_id": f"U{1001234 + user_idx}",
                "account_id": f"AC{1000000 + user_idx}",
                "merchant_id": f"MER{100000 + (i % self.actual_counts['normal_merchants'])}",
                "card_id": f"CARD{100000 + user_idx}",
                "device_id": f"DEV{100000 + user_idx}",
                "amount": round(random.uniform(10, 500), 2),
                "currency": "USD",
                "transaction_type": random.choice(transaction_types),
                "status": "COMPLETED",
                "timestamp": f"2024-01-{random.randint(10,15):02d}T{random.randint(8,20):02d}:{random.randint(0,59):02d}:00Z",
                "location_id": "LOC001",
                "risk_score": round(random.uniform(0.1, 3.0), 1),
                "flags": []
            })
            
        return transactions
    
    def generate_blacklist(self) -> List[Dict[str, Any]]:
        """Generate blacklist data"""
        blacklist_items = []
        
        # Base blacklist items
        base_items = [
            {
                "entity_id": "BL_USER_001",
                "entity_type": "USER",
                "value": "viktor.petrov.crypto@darkweb.net",
                "reason": "Money Laundering Investigation",
                "added_date": "2023-11-20",
                "severity": "HIGH",
                "source": "FBI_SANCTIONS"
            },
            {
                "entity_id": "BL_IP_001", 
                "entity_type": "IP_ADDRESS",
                "value": "185.220.101.47",
                "reason": "Known Tor Exit Node",
                "added_date": "2024-01-01",
                "severity": "MEDIUM",
                "source": "TOR_PROJECT"
            },
            {
                "entity_id": "BL_CARD_001",
                "entity_type": "BIN_RANGE",
                "value": "554700",
                "reason": "High Fraud Rate Prepaid Cards",
                "added_date": "2023-10-15",
                "severity": "HIGH",
                "source": "CARD_NETWORKS"
            }
        ]
        
        blacklist_items.extend(base_items)
        
        # Add blacklist items for each suspicious merchant
        for i, merchant_id in enumerate(self.suspicious_merchant_ids):
            blacklist_items.append({
                "entity_id": f"BL_MERCHANT_{i+1:03d}",
                "entity_type": "MERCHANT",
                "value": merchant_id,
                "reason": f"Unlicensed Cryptocurrency Exchange {i+1}",
                "added_date": f"2023-12-{1 + i % 28:02d}",
                "severity": "VERY_HIGH",
                "source": "TREASURY_SANCTIONS"
            })
            
        return blacklist_items
    
    def generate_risk_scores(self) -> List[Dict[str, Any]]:
        """Generate risk scores history"""
        risk_scores = []
        
        for i, user_id in enumerate(self.suspicious_user_ids):
            risk_scores.append({
                "user_id": user_id,
                "current_score": round(8.7 + i * 0.1, 1),
                "score_history": [
                    {"date": "2024-01-01", "score": round(3.2 + i * 0.1, 1), "reason": "Baseline"},
                    {"date": "2024-01-05", "score": round(4.1 + i * 0.1, 1), "reason": "Increased transaction volume"},
                    {"date": "2024-01-10", "score": round(5.8 + i * 0.1, 1), "reason": "New device login"},
                    {"date": "2024-01-12", "score": round(7.2 + i * 0.1, 1), "reason": "High-risk merchant transactions"},
                    {"date": "2024-01-15", "score": round(8.7 + i * 0.1, 1), "reason": "Suspicious transaction patterns detected"}
                ],
                "risk_factors": [
                    {"factor": "velocity", "weight": 0.25, "score": round(9.1 + i * 0.1, 1)},
                    {"factor": "geography", "weight": 0.20, "score": round(9.8 - i * 0.1, 1)},
                    {"factor": "device", "weight": 0.15, "score": round(9.5 + i * 0.1, 1)},
                    {"factor": "merchant", "weight": 0.20, "score": round(8.9 + i * 0.1, 1)},
                    {"factor": "behavioral", "weight": 0.20, "score": round(7.8 + i * 0.2, 1)}
                ]
            })
            
        return risk_scores
    
    def generate_fraud_alerts(self) -> List[Dict[str, Any]]:
        """Generate fraud alert data"""
        alerts = []
        
        # Main alert for each suspicious transaction
        for i, tx_id in enumerate(self.suspicious_transaction_ids):
            alerts.append({
                "alert_id": f"FRA_2024_{1578 + i:06d}",
                "transaction_id": tx_id,
                "user_id": self.suspicious_user_ids[i],
                "alert_type": "HIGH_VALUE_SUSPICIOUS_TRANSACTION",
                "severity": "CRITICAL",
                "status": "OPEN",
                "created_timestamp": f"2024-01-15T23:{47 - i % 10:02d}:15Z",
                "triggered_rules": [
                    "RULE_001_LARGE_AMOUNT",
                    "RULE_007_NEW_DEVICE",
                    "RULE_015_HIGH_RISK_MERCHANT",
                    "RULE_023_VELOCITY_EXCEEDED",
                    "RULE_031_GEOGRAPHIC_ANOMALY",
                    "RULE_045_VPN_DETECTION"
                ],
                "investigation_priority": 1,
                "estimated_fraud_probability": round(0.947 - i * 0.01, 3),
                "potential_loss": round(487392.85 + i * 50000, 2),
                "assigned_investigator": f"fraud_team_lead_{i+1}" if i > 0 else "fraud_team_lead",
                "sla_deadline": f"2024-01-16T{5 + i % 6:02d}:47:15Z"
            })
            
            # Second alert for the related test transaction
            related_tx_id = f"T8492XJ{1 + i}-1"
            alerts.append({
                "alert_id": f"FRA_2024_{1577 + i:06d}",
                "transaction_id": related_tx_id,
                "alert_type": "VELOCITY_PATTERN",
                "severity": "HIGH",
                "status": "INVESTIGATING",
                "created_timestamp": f"2024-01-15T{22 - i % 2:02d}:15:45Z"
            })
            
        return alerts
    
    def generate_complete_dataset(self) -> Dict[str, Any]:
        """Generate the complete dataset"""
        print(f"Generating live_transactions dataset (scale factor: {self.scale_factor}x, suspicious transactions: {self.suspicious_transactions_count})...")
        
        # Generate all tables
        tables = {
            "users": self.generate_users(),
            "accounts": self.generate_accounts(), 
            "merchants": self.generate_merchants(),
            "cards": self.generate_cards(),
            "devices": self.generate_devices(),
            "live_transactions": self.generate_live_transactions(),
            "locations": [{"location_id": k, **v} for k, v in self.locations.items()],
            "blacklist": self.generate_blacklist(),
            "risk_scores": self.generate_risk_scores(),
            "fraud_alerts": self.generate_fraud_alerts()
        }
        
        # Table record counts
        record_counts = {table: len(data) for table, data in tables.items()}
        
        dataset = {
            "metadata": {
                "dataset_name": "live_transactions_fraud_investigation",
                "generated_timestamp": datetime.datetime.now().isoformat(),
                "scale_factor": self.scale_factor,
                "suspicious_transactions_count": self.suspicious_transactions_count,
                "suspicious_transaction_ids": self.suspicious_transaction_ids,
                "main_suspicious_id": self.main_suspicious_id,
                "total_tables": len(tables),
                "record_counts": record_counts,
                "total_records": sum(record_counts.values()),
                "data_complexity": "HIGH" if self.scale_factor >= 10 else "MEDIUM" if self.scale_factor >= 5 else "STANDARD",
                "fraud_scenario": "Large-scale cryptocurrency money laundering through high-risk offshore exchange"
            },
            "tables": tables
        }
        
        # Add analysis
        dataset["fraud_investigation_summary"] = {
            "suspicious_transactions": [
                {
                    "id": tx_id,
                    "amount_usd": 487392.85 + i * 50000,
                    "risk_indicators": [
                        f"Large amount cryptocurrency conversion (${487392.85 + i * 50000:,.2f})",
                        "Transaction from new device with VPN/Tor",
                        "High-risk merchant with suspended license",
                        "Geographic mismatch (USA user, offshore transaction)",
                        "Preceded by small test transactions",
                        "Part of high-velocity transaction pattern",
                        "Connected to sanctioned entities"
                    ],
                    "investigation_priority": "CRITICAL"
                } for i, tx_id in enumerate(self.suspicious_transaction_ids)
            ],
            "scale_summary": {
                "users": f"{len(tables['users'])} users ({self.suspicious_transactions_count} suspicious)",
                "transactions": f"{len(tables['live_transactions'])} transactions",
                "merchants": f"{len(tables['merchants'])} merchants ({self.suspicious_transactions_count} high-risk)",
                "total_suspicious_volume": f"${sum(487392.85 + i * 50000 for i in range(self.suspicious_transactions_count)):,.2f}"
            },
            "recommended_actions": [
                "Immediate account freeze for all suspicious users",
                "Enhanced due diligence",
                "Report to financial intelligence unit",
                "Cross-reference with other financial institutions",
                "Trace cryptocurrency wallet addresses"
            ]
        }
        
        return dataset
    
    def export_to_bigquery_format(self, dataset: Dict[str, Any], output_dir: str = "bigquery_tables"):
        """Export tables as BigQuery-compatible JSONL files"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        print(f"\n🔄 Exporting BigQuery files to {output_dir}/ ...")
        
        for table_name, table_data in dataset["tables"].items():
            if not table_data:
                continue
                
            output_file = os.path.join(output_dir, f"{table_name}.jsonl")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for record in table_data:
                    json.dump(record, f, ensure_ascii=False)
                    f.write('\n')
                    
            print(f"  ✅ {table_name}.jsonl ({len(table_data)} records)")
        
        metadata_file = os.path.join(output_dir, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(dataset["metadata"], f, indent=2, ensure_ascii=False)
            
        summary_file = os.path.join(output_dir, "fraud_investigation_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(dataset["fraud_investigation_summary"], f, indent=2, ensure_ascii=False)
            
        print(f"  ✅ metadata.json")
        print(f"  ✅ fraud_investigation_summary.json")
        
        return output_dir
    
    def export_to_csv_format(self, dataset: Dict[str, Any], output_dir: str = "csv_tables"):
        """Export tables as CSV files"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        print(f"\n🔄 Exporting CSV files to {output_dir}/ ...")
        
        for table_name, table_data in dataset["tables"].items():
            if not table_data:
                continue
                
            output_file = os.path.join(output_dir, f"{table_name}.csv")
            
            # Convert lists/dicts to JSON strings for CSV
            processed_data = []
            for record in table_data:
                processed_record = {}
                for key, value in record.items():
                    if isinstance(value, (list, dict)):
                        processed_record[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        processed_record[key] = value
                processed_data.append(processed_record)
            
            if processed_data:
                df = pd.DataFrame(processed_data)
                df.to_csv(output_file, index=False, encoding='utf-8')
                print(f"  ✅ {table_name}.csv ({len(processed_data)} records, {len(df.columns)} columns)")
        
        metadata_file = os.path.join(output_dir, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(dataset["metadata"], f, indent=2, ensure_ascii=False)
            
        summary_file = os.path.join(output_dir, "fraud_investigation_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(dataset["fraud_investigation_summary"], f, indent=2, ensure_ascii=False)
            
        print(f"  ✅ metadata.json")
        print(f"  ✅ fraud_investigation_summary.json")
        
        return output_dir

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate Live Transactions dataset')
    parser.add_argument('--scale', type=int, default=1, help='Data scale factor (default: 1)')
    parser.add_argument('--suspicious-count', type=int, default=1, help='Number of suspicious transactions (default: 1)')
    parser.add_argument('--export-bigquery', action='store_true', help='Export in BigQuery format')
    parser.add_argument('--export-csv', action='store_true', help='Export in CSV format')
    parser.add_argument('--output-dir', type=str, default='bigquery_tables', help='Output directory')
    
    args = parser.parse_args()
    
    # Generate dataset
    generator = LiveTransactionsDataGenerator(
        scale_factor=args.scale,
        suspicious_transactions_count=args.suspicious_count
    )
    dataset = generator.generate_complete_dataset()
    
    # Write full dataset to file
    output_file = "live_transactions_dataset.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Dataset generated.")
    print(f"📁 File saved as: {output_file}")
    print(f"📊 Number of tables: {len(dataset['tables'])}")
    print(f"📈 Total records: {dataset['metadata']['total_records']}")
    print(f"🚨 Suspicious transactions: {', '.join(dataset['metadata']['suspicious_transaction_ids'])}")
    print(f"⚖️ Data complexity: {dataset['metadata']['data_complexity']}")
    
    # Table record stats
    print(f"\n📈 Table stats:")
    for table, count in dataset["metadata"]["record_counts"].items():
        print(f"  • {table}: {count} records")
    
    # Suspicious transaction info
    print(f"\n🎯 Suspicious transactions details:")
    for i, tx_info in enumerate(dataset["fraud_investigation_summary"]["suspicious_transactions"]):
        print(f"  • {tx_info['id']}: ${tx_info['amount_usd']:,.2f}")
    
    # Export BigQuery format
    if args.export_bigquery:
        output_dir = args.output_dir if args.output_dir != 'bigquery_tables' else 'bigquery_tables'
        bigquery_dir = generator.export_to_bigquery_format(dataset, output_dir)
        print(f"\n📤 BigQuery files exported to: {bigquery_dir}/")
        print(f"\n💡 BigQuery import suggestions:")
        print(f"  1. Create dataset: bq mk --dataset your_project:live_transactions")
        print(f"  2. Import tables: bq load --source_format=NEWLINE_DELIMITED_JSON your_project:live_transactions.users {bigquery_dir}/users.jsonl")
    
    # Export CSV format
    if args.export_csv:
        output_dir = args.output_dir if args.output_dir != 'bigquery_tables' else 'csv_tables'
        csv_dir = generator.export_to_csv_format(dataset, output_dir)
        print(f"\n📤 CSV files exported to: {csv_dir}/")
        print(f"\n💡 CSV usage suggestions:")
        print(f"  1. Read in pandas: pd.read_csv('{csv_dir}/live_transactions.csv')")
        print(f"  2. DB import: All major databases support CSV import")
        print(f"  3. Excel: Open CSV files directly in Excel for analysis")
        print(f"  4. For complex fields: use json.loads() to parse JSON-format columns")
    
    return dataset

if __name__ == "__main__":
    main()

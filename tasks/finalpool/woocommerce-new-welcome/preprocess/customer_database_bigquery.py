import json
from datetime import datetime
from typing import Dict, List, Optional
from google.cloud import bigquery
from google.oauth2 import service_account

class CustomerDatabase:
    """BigQuery database for managing customer data"""
    
    def __init__(self, credentials_path: str = "configs/gcp-service_account.keys.json", 
                 project_id: str = "mcp-bench0606", 
                 dataset_id: str = "woocommerce_crm"):
        """Initialize BigQuery connection"""
        self.credentials_path = credentials_path
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = f"{project_id}.{dataset_id}.customers"
        
        # Initialize BigQuery client
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        self.client = bigquery.Client(credentials=credentials, project=project_id)
    
    def add_customer(self, customer_data: Dict) -> bool:
        """Add a new customer to the database"""
        try:
            # Convert datetime strings to proper format
            def convert_timestamp(timestamp_str):
                if not timestamp_str:
                    return None
                try:
                    if 'T' in timestamp_str:
                        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).isoformat()
                    else:
                        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').isoformat()
                except ValueError:
                    return None
            
            row = {
                "woocommerce_id": customer_data.get('woocommerce_id'),
                "email": customer_data.get('email'),
                "first_name": customer_data.get('first_name'),
                "last_name": customer_data.get('last_name'),
                "phone": customer_data.get('phone', ''),
                "date_created": convert_timestamp(customer_data.get('date_created')),
                "first_order_date": convert_timestamp(customer_data.get('first_order_date')),
                "welcome_email_sent": bool(customer_data.get('welcome_email_sent', False)),
                "welcome_email_date": convert_timestamp(customer_data.get('welcome_email_date')),
                "sync_date": convert_timestamp(customer_data.get('sync_date')) or datetime.now().isoformat(),
                "metadata": json.dumps(customer_data.get('metadata', {})) if isinstance(customer_data.get('metadata'), dict) else str(customer_data.get('metadata', '{}'))
            }
            
            # Insert or update customer record
            query = f"""
            MERGE `{self.table_id}` T
            USING (SELECT @woocommerce_id as woocommerce_id) S
            ON T.woocommerce_id = S.woocommerce_id
            WHEN MATCHED THEN
                UPDATE SET 
                    email = @email,
                    first_name = @first_name,
                    last_name = @last_name,
                    phone = @phone,
                    date_created = @date_created,
                    first_order_date = @first_order_date,
                    welcome_email_sent = @welcome_email_sent,
                    welcome_email_date = @welcome_email_date,
                    sync_date = @sync_date,
                    metadata = @metadata
            WHEN NOT MATCHED THEN
                INSERT (woocommerce_id, email, first_name, last_name, phone, 
                        date_created, first_order_date, welcome_email_sent, 
                        welcome_email_date, sync_date, metadata)
                VALUES (@woocommerce_id, @email, @first_name, @last_name, @phone,
                        @date_created, @first_order_date, @welcome_email_sent,
                        @welcome_email_date, @sync_date, @metadata)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("woocommerce_id", "INTEGER", row["woocommerce_id"]),
                    bigquery.ScalarQueryParameter("email", "STRING", row["email"]),
                    bigquery.ScalarQueryParameter("first_name", "STRING", row["first_name"]),
                    bigquery.ScalarQueryParameter("last_name", "STRING", row["last_name"]),
                    bigquery.ScalarQueryParameter("phone", "STRING", row["phone"]),
                    bigquery.ScalarQueryParameter("date_created", "TIMESTAMP", row["date_created"]),
                    bigquery.ScalarQueryParameter("first_order_date", "TIMESTAMP", row["first_order_date"]),
                    bigquery.ScalarQueryParameter("welcome_email_sent", "BOOLEAN", row["welcome_email_sent"]),
                    bigquery.ScalarQueryParameter("welcome_email_date", "TIMESTAMP", row["welcome_email_date"]),
                    bigquery.ScalarQueryParameter("sync_date", "TIMESTAMP", row["sync_date"]),
                    bigquery.ScalarQueryParameter("metadata", "STRING", row["metadata"])
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            query_job.result()  # Wait for completion
            return True
            
        except Exception as e:
            print(f"Error adding customer: {e}")
            return False
    
    def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """Get customer by email address"""
        try:
            query = f"""
            SELECT * FROM `{self.table_id}`
            WHERE email = @email
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("email", "STRING", email)
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            if results:
                row = results[0]
                return dict(row)
            return None
            
        except Exception as e:
            print(f"Error getting customer by email: {e}")
            return None
    
    def get_customer_by_woo_id(self, woo_id: int) -> Optional[Dict]:
        """Get customer by WooCommerce ID"""
        try:
            query = f"""
            SELECT * FROM `{self.table_id}`
            WHERE woocommerce_id = @woo_id
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("woo_id", "INTEGER", woo_id)
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            if results:
                row = results[0]
                return dict(row)
            return None
            
        except Exception as e:
            print(f"Error getting customer by WooCommerce ID: {e}")
            return None
    
    def get_new_customers(self, days: int = 7) -> List[Dict]:
        """Get customers who joined in the last N days"""
        try:
            query = f"""
            SELECT * FROM `{self.table_id}`
            WHERE DATE(first_order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
            ORDER BY first_order_date DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("days", "INTEGER", days)
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting new customers: {e}")
            return []
    
    def get_customers_without_welcome_email(self) -> List[Dict]:
        """Get customers who haven't received welcome email"""
        try:
            query = f"""
            SELECT * FROM `{self.table_id}`
            WHERE welcome_email_sent = false OR welcome_email_sent IS NULL
            ORDER BY date_created DESC
            """
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting customers without welcome email: {e}")
            return []
    
    def mark_welcome_email_sent(self, woo_id: int) -> bool:
        """Mark that welcome email was sent to a customer"""
        try:
            query = f"""
            UPDATE `{self.table_id}`
            SET welcome_email_sent = true,
                welcome_email_date = CURRENT_TIMESTAMP()
            WHERE woocommerce_id = @woo_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("woo_id", "INTEGER", woo_id)
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            query_job.result()  # Wait for completion
            
            return query_job.num_dml_affected_rows > 0
            
        except Exception as e:
            print(f"Error marking welcome email sent: {e}")
            return False
    
    def get_all_customers(self) -> List[Dict]:
        """Get all customers from database"""
        try:
            query = f"""
            SELECT * FROM `{self.table_id}`
            ORDER BY sync_date DESC
            """
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting all customers: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_customers,
                COUNT(CASE WHEN DATE(first_order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN 1 END) as new_customers_7_days,
                COUNT(CASE WHEN welcome_email_sent = true THEN 1 END) as welcome_emails_sent,
                COUNT(CASE WHEN welcome_email_sent = false OR welcome_email_sent IS NULL THEN 1 END) as pending_welcome_emails
            FROM `{self.table_id}`
            """
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if results:
                row = results[0]
                return dict(row)
            else:
                return {
                    'total_customers': 0,
                    'new_customers_7_days': 0,
                    'welcome_emails_sent': 0,
                    'pending_welcome_emails': 0
                }
                
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {
                'total_customers': 0,
                'new_customers_7_days': 0,
                'welcome_emails_sent': 0,
                'pending_welcome_emails': 0
            }
    
    def close(self):
        """Close database connection (for BigQuery, this is a no-op)"""
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
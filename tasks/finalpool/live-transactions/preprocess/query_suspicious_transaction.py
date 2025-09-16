#!/usr/bin/env python3
"""
可疑交易调查数据查询脚本

模拟实时交易监控系统中检测到可疑交易后的数据收集和调查流程。
根据可疑交易ID查询所有相关数据，并生成完整的调查档案。
"""

import json
import os
import argparse
import pandas as pd
import csv
from typing import Dict, List, Any, Optional
from datetime import datetime

class SuspiciousTransactionInvestigator:
    """可疑交易调查器 - 负责收集和分析与可疑交易相关的所有数据"""
    
    def __init__(self, dataset_file: str = "live_transactions_dataset.json"):
        """
        初始化调查器
        
        Args:
            dataset_file: 数据集文件路径
        """
        self.dataset_file = dataset_file
        self.dataset = self._load_dataset()
        
    def _load_dataset(self) -> Dict[str, Any]:
        """加载数据集"""
        if not os.path.exists(self.dataset_file):
            raise FileNotFoundError(f"数据集文件未找到: {self.dataset_file}")
            
        with open(self.dataset_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_from_jsonl_tables(self, tables_dir: str) -> Dict[str, Any]:
        """从JSONL表文件加载数据集"""
        dataset = {"tables": {}}
        
        # 加载所有JSONL表文件
        for filename in os.listdir(tables_dir):
            if filename.endswith('.jsonl'):
                table_name = filename[:-6]  # 去掉.jsonl后缀
                table_data = []
                
                with open(os.path.join(tables_dir, filename), 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            table_data.append(json.loads(line))
                
                dataset["tables"][table_name] = table_data
        
        # 加载元数据
        metadata_file = os.path.join(tables_dir, "metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                dataset["metadata"] = json.load(f)
        
        return dataset
    
    def _load_from_csv_tables(self, tables_dir: str) -> Dict[str, Any]:
        """从CSV表文件加载数据集"""
        dataset = {"tables": {}}
        
        # 加载所有CSV表文件
        for filename in os.listdir(tables_dir):
            if filename.endswith('.csv'):
                table_name = filename[:-4]  # 去掉.csv后缀
                file_path = os.path.join(tables_dir, filename)
                
                try:
                    # 使用pandas读取CSV
                    df = pd.read_csv(file_path, encoding='utf-8')
                    
                    # 将DataFrame转换为字典列表
                    table_data = []
                    for _, row in df.iterrows():
                        record = {}
                        for col, value in row.items():
                            # 处理NaN值
                            if pd.isna(value):
                                record[col] = None
                            elif isinstance(value, str) and value.startswith(('[', '{')):
                                # 尝试解析JSON字符串
                                try:
                                    record[col] = json.loads(value)
                                except (json.JSONDecodeError, ValueError):
                                    record[col] = value
                            else:
                                record[col] = value
                        table_data.append(record)
                    
                    dataset["tables"][table_name] = table_data
                    print(f"  📄 加载 {table_name}: {len(table_data)} 条记录")
                    
                except Exception as e:
                    print(f"❌ 加载CSV文件失败 {filename}: {str(e)}")
        
        # 加载元数据
        metadata_file = os.path.join(tables_dir, "metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                dataset["metadata"] = json.load(f)
        
        return dataset
    
    def find_suspicious_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """查找可疑交易记录"""
        transactions = self.dataset["tables"]["live_transactions"]
        
        # 处理不同的数据格式
        if isinstance(transactions, dict):
            return transactions.get(transaction_id)
        elif isinstance(transactions, list):
            for tx in transactions:
                if tx.get("transaction_id") == transaction_id:
                    return tx
        
        return None
    
    def get_related_user_data(self, user_id: str) -> Dict[str, Any]:
        """获取用户相关数据"""
        users = self.dataset["tables"]["users"]
        
        # 处理不同的数据格式
        if isinstance(users, dict):
            user_data = users.get(user_id, {})
        else:
            user_data = next((u for u in users if u.get("user_id") == user_id), {})
        
        return user_data
    
    def get_related_account_data(self, account_id: str) -> Dict[str, Any]:
        """获取账户相关数据"""
        accounts = self.dataset["tables"]["accounts"]
        
        if isinstance(accounts, dict):
            return accounts.get(account_id, {})
        else:
            return next((a for a in accounts if a.get("account_id") == account_id), {})
    
    def get_related_merchant_data(self, merchant_id: str) -> Dict[str, Any]:
        """获取商户相关数据"""
        merchants = self.dataset["tables"]["merchants"]
        
        if isinstance(merchants, dict):
            return merchants.get(merchant_id, {})
        else:
            return next((m for m in merchants if m.get("merchant_id") == merchant_id), {})
    
    def get_related_card_data(self, card_id: str) -> Dict[str, Any]:
        """获取银行卡相关数据"""
        cards = self.dataset["tables"]["cards"]
        
        if isinstance(cards, dict):
            return cards.get(card_id, {})
        else:
            return next((c for c in cards if c.get("card_id") == card_id), {})
    
    def get_related_device_data(self, device_id: str) -> Dict[str, Any]:
        """获取设备相关数据"""
        devices = self.dataset["tables"]["devices"]
        
        if isinstance(devices, dict):
            return devices.get(device_id, {})
        else:
            return next((d for d in devices if d.get("device_id") == device_id), {})
    
    def get_location_data(self, location_id: str) -> Dict[str, Any]:
        """获取地理位置数据"""
        locations = self.dataset["tables"]["locations"]
        
        if isinstance(locations, dict):
            return locations.get(location_id, {})
        else:
            return next((l for l in locations if l.get("location_id") == location_id), {})
    
    def get_related_transactions(self, user_id: str, exclude_transaction_id: str) -> List[Dict[str, Any]]:
        """获取用户的其他相关交易"""
        transactions = self.dataset["tables"]["live_transactions"]
        related_txs = []
        
        if isinstance(transactions, dict):
            for tx_id, tx_data in transactions.items():
                if (tx_data.get("user_id") == user_id and 
                    tx_id != exclude_transaction_id):
                    related_txs.append(tx_data)
        else:
            for tx in transactions:
                if (tx.get("user_id") == user_id and 
                    tx.get("transaction_id") != exclude_transaction_id):
                    related_txs.append(tx)
        
        # 按时间戳排序（最新的在前）
        related_txs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return related_txs
    
    def get_risk_score_data(self, user_id: str) -> Dict[str, Any]:
        """获取用户风险评分数据"""
        risk_scores = self.dataset["tables"]["risk_scores"]
        
        if isinstance(risk_scores, dict):
            return risk_scores.get(user_id, {})
        else:
            return next((r for r in risk_scores if r.get("user_id") == user_id), {})
    
    def get_fraud_alerts(self, transaction_id: str) -> List[Dict[str, Any]]:
        """获取相关的欺诈告警"""
        fraud_alerts = self.dataset["tables"]["fraud_alerts"]
        alerts = []
        
        if isinstance(fraud_alerts, dict):
            # 如果是字典格式，查找包含该交易ID的告警
            for alert_data in fraud_alerts.values():
                if isinstance(alert_data, dict):
                    if alert_data.get("transaction_id") == transaction_id:
                        alerts.append(alert_data)
                elif isinstance(alert_data, list):
                    alerts.extend([a for a in alert_data if a.get("transaction_id") == transaction_id])
        else:
            # 如果是列表格式
            alerts = [a for a in fraud_alerts if a.get("transaction_id") == transaction_id]
        
        return alerts
    
    def get_blacklist_matches(self, investigation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查黑名单匹配"""
        blacklist = self.dataset["tables"]["blacklist"]
        matches = []
        
        # 提取需要检查的值
        check_values = {
            "user_email": investigation_data.get("user_data", {}).get("email"),
            "merchant_id": investigation_data.get("merchant_data", {}).get("merchant_id"),
            "ip_address": investigation_data.get("device_data", {}).get("ip_address"),
            "card_bin": investigation_data.get("card_data", {}).get("card_number_masked", "")[:6]
        }
        
        if isinstance(blacklist, dict):
            blacklist_items = blacklist.get("blacklisted_entities", [])
        else:
            blacklist_items = blacklist
        
        for item in blacklist_items:
            item_value = item.get("value", "")
            for check_key, check_value in check_values.items():
                if check_value and str(check_value).startswith(str(item_value)):
                    matches.append({
                        "matched_field": check_key,
                        "matched_value": check_value,
                        "blacklist_entry": item
                    })
        
        return matches
    
    def calculate_investigation_summary(self, investigation_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算调查总结"""
        transaction = investigation_data["transaction_data"]
        
        # 风险等级评估
        risk_score = transaction.get("risk_score", 0)
        if risk_score >= 9.0:
            risk_level = "CRITICAL"
        elif risk_score >= 7.0:
            risk_level = "HIGH"
        elif risk_score >= 5.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # 统计相关交易
        related_count = len(investigation_data.get("related_transactions", []))
        
        # 统计风险标识
        flags = transaction.get("flags", [])
        flag_count = len(flags)
        
        # 检查设备风险
        device_data = investigation_data.get("device_data", {})
        device_risks = []
        if device_data.get("vpn_detected"):
            device_risks.append("VPN_DETECTED")
        if device_data.get("tor_detected"):
            device_risks.append("TOR_DETECTED")
        if device_data.get("proxy_detected"):
            device_risks.append("PROXY_DETECTED")
        
        # 地理风险
        geo_data = transaction.get("geographic_data", {})
        geo_risk = geo_data.get("unusual_location", False)
        
        # 商户风险
        merchant_data = investigation_data.get("merchant_data", {})
        merchant_risk = merchant_data.get("risk_rating", "LOW")
        
        return {
            "investigation_id": f"INV_{transaction['transaction_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "risk_assessment": {
                "overall_risk_level": risk_level,
                "risk_score": risk_score,
                "total_risk_flags": flag_count,
                "device_risk_count": len(device_risks),
                "geographic_risk": geo_risk,
                "merchant_risk_level": merchant_risk
            },
            "transaction_pattern": {
                "related_transactions_count": related_count,
                "transaction_amount": transaction.get("amount", 0),
                "transaction_type": transaction.get("transaction_type", ""),
                "velocity_flags": len(transaction.get("velocity_checks", {}))
            },
            "blacklist_matches": len(investigation_data.get("blacklist_matches", [])),
            "fraud_alerts_count": len(investigation_data.get("fraud_alerts", [])),
            "investigation_priority": "URGENT" if risk_level == "CRITICAL" else "HIGH" if risk_level == "HIGH" else "NORMAL",
            "recommended_actions": self._get_recommended_actions(risk_level, investigation_data),
            "investigation_timestamp": datetime.now().isoformat(),
            "estimated_fraud_probability": transaction.get("ml_fraud_score", 0) / 100.0 if transaction.get("ml_fraud_score") else None
        }
    
    def _get_recommended_actions(self, risk_level: str, investigation_data: Dict[str, Any]) -> List[str]:
        """生成推荐的调查行动"""
        actions = []
        
        if risk_level == "CRITICAL":
            actions.extend([
                "IMMEDIATE_ACCOUNT_FREEZE",
                "CONTACT_LAW_ENFORCEMENT",
                "REGULATORY_REPORTING_REQUIRED",
                "ENHANCED_DUE_DILIGENCE"
            ])
        elif risk_level == "HIGH":
            actions.extend([
                "ACCOUNT_MONITORING_ENHANCED",
                "MANUAL_REVIEW_REQUIRED",
                "CUSTOMER_CONTACT_VERIFICATION"
            ])
        
        # 基于具体风险因素的行动
        device_data = investigation_data.get("device_data", {})
        if device_data.get("tor_detected") or device_data.get("vpn_detected"):
            actions.append("DEVICE_ANALYSIS_REQUIRED")
        
        if investigation_data.get("blacklist_matches"):
            actions.append("SANCTIONS_SCREENING_REVIEW")
        
        merchant_data = investigation_data.get("merchant_data", {})
        if merchant_data.get("license_status") == "SUSPENDED":
            actions.append("MERCHANT_RELATIONSHIP_REVIEW")
        
        return actions
    
    def investigate_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        完整的可疑交易调查流程
        
        Args:
            transaction_id: 可疑交易ID
            
        Returns:
            完整的调查档案JSON对象
        """
        print(f"🔍 开始调查可疑交易: {transaction_id}")
        
        # 1. 查找主要交易记录
        transaction_data = self.find_suspicious_transaction(transaction_id)
        if not transaction_data:
            raise ValueError(f"未找到交易ID: {transaction_id}")
        
        print(f"✅ 找到交易记录，金额: ${transaction_data.get('amount', 0):,.2f}")
        
        # 2. 收集相关实体数据
        user_id = transaction_data.get("user_id")
        account_id = transaction_data.get("account_id")
        merchant_id = transaction_data.get("merchant_id")
        card_id = transaction_data.get("card_id")
        device_id = transaction_data.get("device_id")
        location_id = transaction_data.get("location_id")
        
        print(f"📊 收集相关数据: 用户({user_id}), 商户({merchant_id}), 设备({device_id})")
        
        # 3. 构建完整的调查档案
        investigation_data = {
            # 主要交易数据
            "transaction_data": transaction_data,
            
            # 用户数据
            "user_data": self.get_related_user_data(user_id) if user_id else {},
            
            # 账户数据
            "account_data": self.get_related_account_data(account_id) if account_id else {},
            
            # 商户数据
            "merchant_data": self.get_related_merchant_data(merchant_id) if merchant_id else {},
            
            # 银行卡数据
            "card_data": self.get_related_card_data(card_id) if card_id else {},
            
            # 设备数据
            "device_data": self.get_related_device_data(device_id) if device_id else {},
            
            # 地理位置数据
            "location_data": self.get_location_data(location_id) if location_id else {},
            
            # 相关交易记录（最近30天）
            "related_transactions": self.get_related_transactions(user_id, transaction_id) if user_id else [],
            
            # 风险评分历史
            "risk_score_data": self.get_risk_score_data(user_id) if user_id else {},
            
            # 相关欺诈告警
            "fraud_alerts": self.get_fraud_alerts(transaction_id),
        }
        
        # 4. 黑名单匹配检查
        investigation_data["blacklist_matches"] = self.get_blacklist_matches(investigation_data)
        
        # 5. 生成调查总结
        investigation_data["investigation_summary"] = self.calculate_investigation_summary(investigation_data)
        
        print(f"⚠️  风险等级: {investigation_data['investigation_summary']['risk_assessment']['overall_risk_level']}")
        print(f"🚨 欺诈概率: {investigation_data['investigation_summary'].get('estimated_fraud_probability', 'N/A')}")
        print(f"📋 推荐行动: {len(investigation_data['investigation_summary']['recommended_actions'])} 项")
        
        return investigation_data
    
    def save_investigation_report(self, investigation_data: Dict[str, Any], output_file: str = None) -> str:
        """保存调查报告"""
        transaction_id = investigation_data["transaction_data"]["transaction_id"]
        
        if not output_file:
            output_file = f"{transaction_id}_investigation_report.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(investigation_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 调查报告已保存: {output_file}")
        return output_file

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='可疑交易调查工具')
    parser.add_argument('--transaction-id', type=str, default='T8492XJ3', 
                       help='可疑交易ID (默认: T8492XJ3)')
    parser.add_argument('--dataset', type=str, default='live_transactions_dataset.json',
                       help='数据集文件路径')
    parser.add_argument('--tables-dir', type=str, 
                       help='JSONL表文件目录 (如果使用分离的表文件)')
    parser.add_argument('--csv-dir', type=str,
                       help='CSV表文件目录 (如果使用CSV格式的表文件)')
    parser.add_argument('--output', type=str,
                       help='输出文件路径')
    parser.add_argument('--show-summary', action='store_true',
                       help='显示调查摘要')
    
    args = parser.parse_args()
    
    try:
        # 初始化调查器
        if args.csv_dir:
            print(f"📁 从CSV目录加载数据: {args.csv_dir}")
            investigator = SuspiciousTransactionInvestigator.__new__(SuspiciousTransactionInvestigator)
            investigator.dataset = investigator._load_from_csv_tables(args.csv_dir)
        elif args.tables_dir:
            print(f"📁 从JSONL目录加载数据: {args.tables_dir}")
            investigator = SuspiciousTransactionInvestigator.__new__(SuspiciousTransactionInvestigator)
            investigator.dataset = investigator._load_from_jsonl_tables(args.tables_dir)
        else:
            print(f"📁 从JSON文件加载数据: {args.dataset}")
            investigator = SuspiciousTransactionInvestigator(args.dataset)
        
        # 执行调查
        investigation_data = investigator.investigate_transaction(args.transaction_id)
        
        # 显示摘要
        if args.show_summary:
            summary = investigation_data["investigation_summary"]
            print(f"\n📋 调查摘要:")
            print(f"  🆔 调查ID: {summary['investigation_id']}")
            print(f"  ⚠️  风险等级: {summary['risk_assessment']['overall_risk_level']}")
            print(f"  📊 风险评分: {summary['risk_assessment']['risk_score']}/10")
            print(f"  💰 交易金额: ${summary['transaction_pattern']['transaction_amount']:,.2f}")
            print(f"  🔗 相关交易: {summary['transaction_pattern']['related_transactions_count']} 笔")
            print(f"  🚨 欺诈告警: {summary['fraud_alerts_count']} 个")
            print(f"  ⚖️ 推荐优先级: {summary['investigation_priority']}")
            
            print(f"\n📝 推荐行动:")
            for action in summary['recommended_actions']:
                print(f"    • {action}")
        
        # 保存报告
        output_file = investigator.save_investigation_report(investigation_data, args.output)
        
        print(f"\n✅ 调查完成！完整的调查档案已生成。")
        print(f"📄 文件大小: {os.path.getsize(output_file) / 1024:.1f} KB")
        
        return investigation_data
        
    except Exception as e:
        print(f"❌ 调查失败: {str(e)}")
        return None

if __name__ == "__main__":
    main() 
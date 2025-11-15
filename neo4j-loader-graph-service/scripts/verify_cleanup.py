#!/usr/bin/env python3
"""Quick script to verify cleanup results."""

import re

# Read the cleaned predictions file
with open('predictions_cleaned.txt', 'r', encoding='utf-8') as f:
    data = f.read()

# Extract all predictions
predictions = []
for block in data.split('=' * 80)[1:]:  # Skip header
    if not block.strip():
        continue
    
    group_id_match = re.search(r'Group ID:\s+(\S+)', block)
    domain_match = re.search(r'Domain:\s+(\w+)', block)
    model_version_match = re.search(r'Model Version:\s+(\S+)', block)
    
    if group_id_match and domain_match and model_version_match:
        predictions.append({
            'group_id': group_id_match.group(1),
            'domain': domain_match.group(1),
            'model_version': model_version_match.group(1)
        })

# Check for model version 1
model_v1 = [p for p in predictions if p['model_version'] == '1']
print(f"✅ Predictions with model version 1: {len(model_v1)}")

# Check for duplicate BTC predictions per group
groups = {}
for p in predictions:
    if p['domain'] == 'btc':
        groups.setdefault(p['group_id'], []).append(p)

duplicates = {k: v for k, v in groups.items() if len(v) > 1}
print(f"✅ Groups with duplicate BTC predictions: {len(duplicates)}")

if duplicates:
    print("\n⚠️  Found duplicates:")
    for group_id, preds in duplicates.items():
        print(f"  Group {group_id}: {len(preds)} BTC predictions")
else:
    print("   No duplicates found!")

# Summary
print(f"\n📊 SUMMARY:")
print(f"   Total predictions: {len(predictions)}")
print(f"   Unique groups: {len(set(p['group_id'] for p in predictions))}")
print(f"   Model versions: {sorted(set(p['model_version'] for p in predictions))}")
print(f"   Domains: {sorted(set(p['domain'] for p in predictions))}")
print(f"   BTC predictions: {len([p for p in predictions if p['domain'] == 'btc'])}")
print(f"   Conflict predictions: {len([p for p in predictions if p['domain'] == 'conflict'])}")


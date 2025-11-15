# Feature Engineering Service - TODO List

**Service**: feature-engineering-service
**Version**: 0.2.5
**Last Updated**: 2025-11-14
**Status**: In Development - Async Migration Complete

---

## Current Sprint: Async Migration and Connection Pool Implementation ✅ COMPLETE

### Task 1: BTC Price Feature Extractor ✅ COMPLETE
- [x] Create src/extractors/btc_price_extractor.py
  - [x] Implement BtcPriceExtractor class extending BaseExtractor
  - [x] Fetch BTC price data from PostgreSQL btc_truth table
  - [x] Extract features: change_pct_10h, volatility_score, volume, label_spike
  - [x] Compute temporal alignment with semantic groups (±1 hour window)
  - [x] Handle missing BTC data gracefully (use default values or skip)
  - [x] Add comprehensive logging with BTC price values
  - [x] Add error handling for database queries

### Task 2: BTC Feature Integration ✅ COMPLETE
- [x] Update src/service.py to include BTC price extractor
  - [x] Add BtcPriceExtractor to extractor chain
  - [x] Integrate BTC features with semantic group features
  - [x] Update feature count from 24 to 28 (4 new BTC features)
  - [x] Add logging for BTC feature extraction

### Task 3: Feast Feature View Update ✅ COMPLETE
- [x] Update src/feast/feature_definitions.py
  - [x] Add 4 new BTC price features to schema
  - [x] Update feature view with BTC features
  - [x] Maintain backward compatibility with existing features
  - [x] Feature version remains v1.0 (backward compatible)

### Task 4: Delta Lake Schema Update
- [ ] Update src/storage/delta_writer.py
  - [ ] Add BTC feature columns to Delta Lake schema
  - [ ] Handle schema evolution for existing tables
  - [ ] Test UPSERT logic with new columns

### Task 5: Redis Online Store Update
- [ ] Update src/clients/redis_client.py
  - [ ] Ensure BTC features are written to Redis
  - [ ] Update feature serialization to include BTC features
  - [ ] Test online feature retrieval with BTC features

### Task 6: Feature Validation Update
- [ ] Update src/validation/feature_validator.py
  - [ ] Add validation rules for BTC features
  - [ ] Validate change_pct_10h range (reasonable percentage)
  - [ ] Validate volatility_score (non-negative)
  - [ ] Validate volume (non-negative)
  - [ ] Validate label_spike (boolean)

### Task 7: Configuration Update
- [ ] Update src/config.py
  - [ ] Add BTC feature extraction configuration
  - [ ] Add temporal alignment window parameter
  - [ ] Add BTC feature enable/disable flag

### Task 8: Testing
- [ ] Create tests/unit/test_btc_price_extractor.py
  - [ ] Test BTC price data fetching
  - [ ] Test temporal alignment logic
  - [ ] Test feature extraction
  - [ ] Test error handling
  - [ ] Achieve ≥90% coverage

### Task 9: Integration Testing
- [ ] Test end-to-end with BTC data
  - [ ] Verify BTC features are extracted
  - [ ] Verify BTC features are written to Feast
  - [ ] Verify BTC features are written to Redis
  - [ ] Verify BTC features are published to Kafka

### Task 10: Documentation
- [ ] Update CHANGELOG.md with BTC feature integration
- [ ] Update TODO.md with completion status
- [ ] Add BTC feature documentation to README.md

---

## Summary

**Total Tasks**: 10
**Completed**: 3
**In Progress**: 1 (Task 4 - Delta Lake Schema Update)
**Remaining**: 6

**Current Phase**: BTC Price Feature Integration
**Next Milestone**: Complete testing and validation

---

**Last Updated**: 2025-11-09  
**Maintainer**: Feature Engineering Service Team


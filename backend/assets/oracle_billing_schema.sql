-- ============================================================
-- ORACLE BILLING DATABASE SCHEMA
-- System: Oracle E-Business Suite + Custom Billing Extensions
-- Version: 12.1.3 + Telecom Billing Module v7.4.2
-- Exported: 2024-01-15 by DBA team (partial - billing extension only)
-- NOTE: Core EBS schema not included. Only custom TELCO_BILLING schema.
-- WARNING: Several tables are undocumented. Reverse engineered from code.
-- Schema owner: TELCO_BILLING (app user: BILLING_APP, BILLING_BATCH)
-- ============================================================

-- ============================================================
-- PRODUCT CATALOG
-- Authoritative product/plan master. Referenced by Amdocs CRM
-- and Netcracker via cross-schema DB link and REST.
-- ============================================================

CREATE TABLE TELCO_BILLING.PRODUCT_CATALOG (
    PRODUCT_CODE        VARCHAR2(30)    NOT NULL,
    PRODUCT_NAME        VARCHAR2(200)   NOT NULL,
    PRODUCT_CATEGORY    VARCHAR2(30)    NOT NULL,   -- BROADBAND, FIBER, VOIP, MOBILE, IPTV, ENTERPRISE, BUNDLE
    PRODUCT_TYPE        VARCHAR2(20)    NOT NULL,   -- BASE, ADDON, BUNDLE, PROMO
    BILLING_MODEL       VARCHAR2(20)    NOT NULL,   -- FLAT_RATE, USAGE_BASED, TIERED, HYBRID
    BASE_CHARGE         NUMBER(10,2),               -- NULL for usage-only products
    SETUP_FEE           NUMBER(10,2)    DEFAULT 0,
    TAX_CLASS           VARCHAR2(20),               -- Maps to tax engine. Undocumented values observed: TELCO_SVC, TELCO_DATA, EXEMPT, GOV_EXEMPT
    BILLING_CYCLE       VARCHAR2(10)    DEFAULT 'MONTHLY',  -- MONTHLY, QUARTERLY, ANNUAL, ON_DEMAND
    STATUS              VARCHAR2(10)    NOT NULL,   -- ACTIVE, SUNSET, RETIRED, DRAFT
    EFFECTIVE_DT        DATE            NOT NULL,
    SUNSET_DT           DATE,                       -- When NULL, product is indefinitely active
    NC_PRODUCT_ID       VARCHAR2(30),               -- Netcracker product reference. NULL for ~80 legacy products.
    LEGACY_PROD_CODE    VARCHAR2(20),               -- Old product code pre-2015 migration. Used in some JIL jobs.
    GL_ACCOUNT          VARCHAR2(30),               -- General Ledger account code. Finance system reference.
    CREATED_BY          VARCHAR2(50),
    LAST_UPD_DT         DATE,
    NOTES               VARCHAR2(1000), -- Business rules, exceptions. Often outdated.
    CONSTRAINT PK_PRODUCT_CATALOG PRIMARY KEY (PRODUCT_CODE)
);

-- Known issues:
-- 1. 47 RETIRED products still have active subscriptions in Amdocs CUSTOMER_PRODUCT (data inconsistency)
-- 2. NC_PRODUCT_ID NULL for 80 legacy products breaks Netcracker resource assignment
-- 3. TAX_CLASS values inconsistent - 'TELCO_SVC' and 'TELCO_SERVICE' both exist for same tax treatment
-- 4. No FK from Amdocs CRM to this table - enforced only at application layer (frequently violated)

-- ============================================================
-- BILLING ACCOUNT
-- One customer can have multiple billing accounts (corporate hierarchies).
-- This is the central node for all financial transactions.
-- ============================================================

CREATE TABLE TELCO_BILLING.BILLING_ACCOUNT (
    BILLING_ACCT_ID     NUMBER(15)      NOT NULL,
    CUST_ID             VARCHAR2(20)    NOT NULL,   -- Amdocs CUST_ID. VARCHAR2 not NUMBER - type mismatch causes implicit conversion in joins.
    ACCT_TYPE           VARCHAR2(20)    NOT NULL,   -- RESIDENTIAL, BUSINESS, CORPORATE_PARENT, CORPORATE_CHILD, WHOLESALE, GOVERNMENT
    PAYMENT_METHOD      VARCHAR2(20),               -- CREDIT_CARD, DIRECT_DEBIT, INVOICE, WIRE_TRANSFER, CHECK
    BILLING_CYCLE_DAY   NUMBER(2),                  -- Day of month billing runs. 1, 8, 15, 22, or 28.
    CURRENCY_CODE       VARCHAR2(3)     DEFAULT 'USD',
    CREDIT_LIMIT        NUMBER(12,2),
    CURRENT_BALANCE     NUMBER(12,2),               -- WARNING: Updated by batch, not real-time. Lag up to 24hrs.
    STATUS              VARCHAR2(10)    NOT NULL,   -- ACTIVE, SUSPENDED, CLOSED, COLLECTIONS, WRITE_OFF
    DUNNING_LEVEL       NUMBER(1)       DEFAULT 0,  -- 0=None, 1=First notice, 2=Second notice, 3=Collections, 4=Legal
    PAPER_BILL_FLAG     VARCHAR2(1)     DEFAULT 'N',
    EBILL_EMAIL         VARCHAR2(200),
    TAX_EXEMPT_FLAG     VARCHAR2(1)     DEFAULT 'N',
    TAX_EXEMPT_CERT     VARCHAR2(50),               -- Tax exemption certificate number. Not validated.
    PARENT_ACCT_ID      NUMBER(15),                 -- Self-referencing FK for corporate hierarchy. Max 3 levels enforced in app only.
    CREATED_DT          DATE            NOT NULL,
    LAST_UPD_DT         DATE,
    CONSTRAINT PK_BILLING_ACCOUNT PRIMARY KEY (BILLING_ACCT_ID)
);

-- CRITICAL ISSUE: CUST_ID is VARCHAR2 but Amdocs CUSTOMER_MASTER.CUST_ID is NUMBER(15)
-- Every join forces implicit type conversion - causing full table scans, index bypass
-- Estimated query performance impact: 3-8x slower than necessary
-- Fix: Type alignment - requires coordinated schema change across both systems

-- ============================================================
-- INVOICE
-- Monthly invoices. High volume. Partitioned by INVOICE_DT (monthly).
-- ============================================================

CREATE TABLE TELCO_BILLING.INVOICE (
    INVOICE_ID          NUMBER(15)      NOT NULL,
    BILLING_ACCT_ID     NUMBER(15)      NOT NULL,   -- FK to BILLING_ACCOUNT
    INVOICE_NUM         VARCHAR2(30)    NOT NULL,   -- Human-readable. Format: INV-YYYYMM-NNNNNNNN
    INVOICE_DT          DATE            NOT NULL,
    DUE_DT              DATE            NOT NULL,
    BILLING_PERIOD_FROM DATE            NOT NULL,
    BILLING_PERIOD_TO   DATE            NOT NULL,
    SUBTOTAL            NUMBER(12,2)    NOT NULL,
    TAX_AMOUNT          NUMBER(12,2)    NOT NULL,
    DISCOUNT_AMOUNT     NUMBER(12,2)    DEFAULT 0,
    TOTAL_AMOUNT        NUMBER(12,2)    NOT NULL,
    STATUS              VARCHAR2(20)    NOT NULL,   -- DRAFT, ISSUED, PAID, PARTIALLY_PAID, OVERDUE, VOID, WRITTEN_OFF
    PAID_AMOUNT         NUMBER(12,2)    DEFAULT 0,
    PAID_DT             DATE,
    GENERATED_BY        VARCHAR2(30),               -- BATCH_MONTHLY, BATCH_ADHOC, MANUAL, PRORATE_JOB
    PDF_STORED          VARCHAR2(1)     DEFAULT 'N', -- Y=PDF stored in document mgmt. N=regenerated on demand.
    PDF_PATH            VARCHAR2(500),              -- Filesystem path. NFS mount. Sometimes stale after storage migration.
    DISPUTE_FLAG        VARCHAR2(1)     DEFAULT 'N',
    CONSTRAINT PK_INVOICE PRIMARY KEY (INVOICE_ID),
    CONSTRAINT UQ_INVOICE_NUM UNIQUE (INVOICE_NUM)
) PARTITION BY RANGE (INVOICE_DT) INTERVAL (NUMTOYMINTERVAL(1,'MONTH'))
  (PARTITION INV_BEFORE_2020 VALUES LESS THAN (DATE '2020-01-01'));

-- ============================================================
-- INVOICE LINE ITEM
-- Individual charges per invoice. Very high volume.
-- ============================================================

CREATE TABLE TELCO_BILLING.INVOICE_LINE_ITEM (
    LINE_ITEM_ID        NUMBER(18)      NOT NULL,
    INVOICE_ID          NUMBER(15)      NOT NULL,
    BILLING_ACCT_ID     NUMBER(15)      NOT NULL,   -- Denormalized from invoice for batch performance
    PRODUCT_CODE        VARCHAR2(30)    NOT NULL,
    SERVICE_ID          VARCHAR2(50),               -- Netcracker service reference
    CHARGE_TYPE         VARCHAR2(30)    NOT NULL,   -- RECURRING, ONETIME, USAGE, CREDIT, ADJUSTMENT, PRORATE, PENALTY
    DESCRIPTION         VARCHAR2(500)   NOT NULL,
    QUANTITY            NUMBER(10,4)    DEFAULT 1,
    UNIT_RATE           NUMBER(12,6),               -- 6 decimal places for usage-based billing
    CHARGE_AMOUNT       NUMBER(12,2)    NOT NULL,
    TAX_AMOUNT          NUMBER(12,2)    DEFAULT 0,
    TAX_CODE            VARCHAR2(20),
    DISCOUNT_AMOUNT     NUMBER(12,2)    DEFAULT 0,
    PROMO_CODE          VARCHAR2(20),
    BILLING_PERIOD_FROM DATE,
    BILLING_PERIOD_TO   DATE,
    USAGE_DETAIL_ID     NUMBER(15),                 -- FK to USAGE_DETAIL for usage-based charges
    GL_ACCOUNT          VARCHAR2(30),
    REVENUE_RECOGNIZED  VARCHAR2(1)     DEFAULT 'N', -- Revenue recognition flag for finance
    CONSTRAINT PK_INVOICE_LINE_ITEM PRIMARY KEY (LINE_ITEM_ID)
) PARTITION BY RANGE (BILLING_PERIOD_FROM) INTERVAL (NUMTOYMINTERVAL(1,'MONTH'))
  (PARTITION ILI_BEFORE_2020 VALUES LESS THAN (DATE '2020-01-01'));

-- ============================================================
-- USAGE DETAIL
-- Raw usage records before rating. CDRs, data usage, API calls.
-- Extremely high volume - ~250M records/month for voice alone.
-- ============================================================

CREATE TABLE TELCO_BILLING.USAGE_DETAIL (
    USAGE_ID            NUMBER(18)      NOT NULL,
    BILLING_ACCT_ID     NUMBER(15)      NOT NULL,
    SERVICE_ID          VARCHAR2(50),
    USAGE_TYPE          VARCHAR2(20)    NOT NULL,   -- VOICE_CALL, SMS, DATA_MB, API_CALL, ROAMING_VOICE, ROAMING_DATA
    USAGE_DT            TIMESTAMP       NOT NULL,
    DURATION_SECS       NUMBER(10),                 -- For voice calls
    VOLUME_MB           NUMBER(12,4),               -- For data usage
    ORIGIN              VARCHAR2(50),               -- Source system: SWITCH, RADIUS, GGSN, SMSC
    DESTINATION         VARCHAR2(50),
    RATED_FLAG          VARCHAR2(1)     DEFAULT 'N', -- N=Unrated, Y=Rated, E=Rating Error, D=Duplicate
    RATED_AMOUNT        NUMBER(12,6),
    RATED_DT            TIMESTAMP,
    RATE_PLAN_CODE      VARCHAR2(30),
    MEDIATION_ID        VARCHAR2(50),               -- Source mediation system batch ID
    RAW_RECORD_HASH     VARCHAR2(64),               -- MD5 hash for duplicate detection. Not all sources populate this.
    CONSTRAINT PK_USAGE_DETAIL PRIMARY KEY (USAGE_ID)
) PARTITION BY RANGE (USAGE_DT) INTERVAL (NUMTOYMINTERVAL(1,'MONTH'))
  (PARTITION UD_BEFORE_2020 VALUES LESS THAN (DATE '2020-01-01'))
  COMPRESS FOR OLTP;

-- ============================================================
-- PAYMENT
-- ============================================================

CREATE TABLE TELCO_BILLING.PAYMENT (
    PAYMENT_ID          NUMBER(15)      NOT NULL,
    BILLING_ACCT_ID     NUMBER(15)      NOT NULL,
    INVOICE_ID          NUMBER(15),                 -- NULL for account-level payments (applied to oldest invoice)
    PAYMENT_DT          DATE            NOT NULL,
    AMOUNT              NUMBER(12,2)    NOT NULL,
    PAYMENT_METHOD      VARCHAR2(20),
    REFERENCE_NUM       VARCHAR2(100),              -- Bank reference, check number, card auth code
    STATUS              VARCHAR2(20)    NOT NULL,   -- PENDING, CLEARED, FAILED, REVERSED, REFUNDED
    REVERSAL_ID         NUMBER(15),                 -- FK to self (reversed payment)
    PAYMENT_SOURCE      VARCHAR2(30),               -- IVR, ONLINE_PORTAL, AUTOPAY, AGENT, BATCH_DIRECT_DEBIT, WESTERN_UNION
    PROCESSOR_RESPONSE  VARCHAR2(500),              -- Raw payment processor response. Contains PII in some legacy records.
    CONSTRAINT PK_PAYMENT PRIMARY KEY (PAYMENT_ID)
);

-- SECURITY ISSUE: PROCESSOR_RESPONSE column contains raw payment processor 
-- responses from pre-2018 which may include partial card numbers. 
-- PCI-DSS audit finding OA-2022-047 - not yet remediated.

-- ============================================================
-- BATCH JOB CONTROL (Undocumented - reverse engineered)
-- Controls monthly billing batch execution sequence.
-- ============================================================

CREATE TABLE TELCO_BILLING.BATCH_JOB_CONTROL (
    JOB_ID              VARCHAR2(50)    NOT NULL,   -- Matches JIL job name
    JOB_DESCRIPTION     VARCHAR2(200),
    EXECUTION_ORDER     NUMBER(5),                  -- Sequence within batch. Gaps exist (numbered 10,20,30...) some filled in ad-hoc as 11,12,21
    DEPENDS_ON_JOB      VARCHAR2(50),               -- Single parent dependency only. Multi-parent not supported.
    LAST_START_DT       TIMESTAMP,
    LAST_END_DT         TIMESTAMP,
    LAST_STATUS         VARCHAR2(20),               -- SUCCESS, FAILED, RUNNING, ABORTED, SKIPPED
    LAST_RECORDS_PROC   NUMBER(15),
    AVERAGE_RUNTIME_MIN NUMBER(10,2),
    SLA_RUNTIME_MIN     NUMBER(10,2),               -- SLA breach threshold. NULL for jobs added after original design.
    RETRY_COUNT         NUMBER(2)       DEFAULT 0,
    MAX_RETRIES         NUMBER(2)       DEFAULT 3,
    ON_FAILURE_ACTION   VARCHAR2(20)    DEFAULT 'ALERT',  -- ALERT, SKIP, ABORT_ALL, RETRY
    ENABLED_FLAG        VARCHAR2(1)     DEFAULT 'Y',
    NOTES               VARCHAR2(2000), -- Ad-hoc notes from ops team. Critical business logic documented here instead of proper docs.
    CONSTRAINT PK_BATCH_JOB_CONTROL PRIMARY KEY (JOB_ID)
);

-- ============================================================
-- BATCH JOB SEQUENCE (the actual monthly billing run)
-- ============================================================

-- Batch sequence as documented in BATCH_JOB_CONTROL + reverse engineered from JIL:

INSERT INTO TELCO_BILLING.BATCH_JOB_CONTROL VALUES
('BILL_001_CLOSE_PERIOD',   'Close billing period, lock usage',    10, NULL,           NULL,NULL,'SUCCESS',NULL,45.2,60,0,3,'ABORT_ALL','CRITICAL: Must complete before any rating jobs. If this fails, entire billing run aborts.'),
('BILL_010_RATE_VOICE',     'Rate voice CDRs from mediation',       20, 'BILL_001_CLOSE_PERIOD', NULL,NULL,'SUCCESS',NULL,180.5,240,0,3,'ABORT_ALL','Sources from USAGE_DETAIL where USAGE_TYPE=VOICE_CALL and RATED_FLAG=N'),
('BILL_011_RATE_DATA',      'Rate data usage records',              21, 'BILL_001_CLOSE_PERIOD', NULL,NULL,'SUCCESS',NULL,95.3,120,0,3,'ABORT_ALL','Separate from voice to allow parallel run - but scheduler runs sequential due to OA-2019-003 incident'),
('BILL_012_RATE_ROAMING',   'Rate roaming CDRs (partner files)',    22, 'BILL_001_CLOSE_PERIOD', NULL,NULL,'SUCCESS',NULL,22.1,45,0,3,'ALERT','Depends on partner file arrival by 23:00. If late, runs with N/A flag. Finance manually adjusts.'),
('BILL_020_APPLY_PROMOS',   'Apply promotional discounts',          30, 'BILL_011_RATE_DATA',    NULL,NULL,'SUCCESS',NULL,38.7,60,0,3,'ALERT','KNOWN ISSUE: Does not handle stacked promos correctly. Manual correction for ~200 accounts monthly.'),
('BILL_030_GENERATE_INV',   'Generate invoices for all accounts',  40, 'BILL_020_APPLY_PROMOS', NULL,NULL,'SUCCESS',NULL,95.8,120,0,3,'ABORT_ALL','Calls PKG_INVOICE.GENERATE_ALL. Single-threaded. Bottleneck for batch SLA.'),
('BILL_040_TAX_CALC',       'Calculate taxes via external engine',  50, 'BILL_030_GENERATE_INV', NULL,NULL,'SUCCESS',NULL,62.4,90,0,3,'ABORT_ALL','External tax engine API call. If tax engine down, entire batch fails. No fallback.'),
('BILL_050_FINALIZE_INV',   'Finalize and issue invoices',          60, 'BILL_040_TAX_CALC',     NULL,NULL,'SUCCESS',NULL,28.2,45,0,3,'ABORT_ALL',NULL),
('BILL_060_AUTOPAY',        'Process autopay/direct debit',         70, 'BILL_050_FINALIZE_INV', NULL,NULL,'SUCCESS',NULL,44.1,60,0,2,'ALERT','Calls bank API. Failure here does NOT abort batch - payments retried next day.'),
('BILL_070_DUNNING',        'Identify overdue accounts, send notices',80,'BILL_050_FINALIZE_INV',NULL,NULL,'SUCCESS',NULL,15.3,30,0,3,'ALERT',NULL),
('BILL_080_SYNC_CRM',       'Sync billing status back to Amdocs CRM',90,'BILL_050_FINALIZE_INV',NULL,NULL,'SUCCESS',NULL,35.6,60,0,3,'ALERT','Calls SP_SYNC_BILLING_ACCT in Amdocs via DB link. Fails 3x/month avg when BILLINK down.'),
('BILL_090_GL_EXPORT',      'Export to GL/Finance system',          100,'BILL_050_FINALIZE_INV',NULL,NULL,'SUCCESS',NULL,18.9,30,0,3,'ALERT','Writes flat file to NFS share. Finance imports manually. No automated handshake.'),
('BILL_099_RECONCILE',      'Reconcile Netcracker inventory vs billing',110,'BILL_090_GL_EXPORT',NULL,NULL,'SUCCESS',NULL,88.4,120,0,3,'ALERT','KNOWN ISSUE: 1.2% divergence rate considered acceptable per business. Root cause not investigated.');

-- ============================================================
-- KEY STORED PROCEDURES (documented via code comments)
-- ============================================================

/*
PKG_BILLING.VALIDATE_PRODUCT
  Called by: Amdocs CRM SP_SUBMIT_ORDER (synchronous)
  Purpose: Validates product code exists and is active in catalog
  Issues: Makes DB link call back to Amdocs to check customer eligibility
           CIRCULAR DEPENDENCY: Amdocs calls Oracle Billing, which calls back to Amdocs
           This circular synchronous call chain causes deadlock under load (incident INC-2023-0445)

PKG_INVOICE.GENERATE_ALL  
  Called by: BILL_030_GENERATE_INV batch job
  Purpose: Generates all monthly invoices
  Issues: Single-threaded PL/SQL loop over all billing accounts
          Cannot be parallelized without major refactor
          Runtime grows linearly with customer base - SLA at risk with projected growth

PKG_INVOICE.GET_BALANCE
  Called by: Amdocs CRM SP_CUSTOMER_360 (synchronous, real-time)
  Purpose: Returns current account balance for CRM display
  Issues: Queries unpartitioned PAYMENT table - P99 latency 3.2 seconds under load
          No caching - called on every CRM customer screen open

PKG_TAX.CALCULATE
  Called by: BILL_040_TAX_CALC batch job AND real-time quote API
  Purpose: Calculates taxes via external Avalara tax engine
  Issues: No local fallback if Avalara unreachable
          Tax rates cached in TELCO_BILLING.TAX_RATE_CACHE table (refreshed weekly)
          Real-time quotes use cached rates; batch billing calls live API - inconsistency possible

PKG_COLLECTIONS.PROCESS_DUNNING
  Called by: BILL_070_DUNNING batch job
  Purpose: Identifies overdue accounts and triggers dunning notices
  Issues: Dunning logic hardcoded in PL/SQL - 847 lines of nested IF/ELSE
          Business rules for dunning exclusions (government, VIP, dispute) intermixed with execution logic
          No unit tests. Last modified 2019. Author no longer with company.
*/

-- ============================================================
-- CROSS-SYSTEM INTEGRATION SUMMARY
-- ============================================================

/*
INBOUND DATA FLOWS TO ORACLE BILLING:
  1. Amdocs CRM → Oracle Billing   : Via DB link BILLINK (synchronous, bidirectional)
                                      + SP calls for product validation
  2. Netcracker  → Oracle Billing  : Via nightly /v1/inventory/export CSV file
                                      + Direct DB query via NCLINK
  3. Mediation Platform → Oracle   : CDR files via SFTP to NFS mount, picked up by BILL_010/011/012
  4. External Tax Engine (Avalara) ↔ Oracle Billing : REST API (outbound for calculation)
  5. Bank/Payment Processors       → Oracle Billing : Via BILL_060_AUTOPAY batch + real-time IVR payments
  
OUTBOUND DATA FLOWS FROM ORACLE BILLING:
  1. Oracle Billing → Amdocs CRM   : Via DB link (BILL_080_SYNC_CRM job)
  2. Oracle Billing → Finance/GL   : NFS flat file (BILL_090_GL_EXPORT job) - manual pickup
  3. Oracle Billing → Document Mgmt: PDF invoice storage (NFS path in PDF_PATH column)
  4. Oracle Billing → Collections  : Output file from PKG_COLLECTIONS to collections agency SFTP

CIRCULAR DEPENDENCY (CRITICAL RISK):
  Amdocs.SP_SUBMIT_ORDER 
    → Oracle.PKG_BILLING.VALIDATE_PRODUCT 
      → Amdocs.CUSTOMER_MASTER (via reverse DB link) 
  = Synchronous circular call chain. Under high order volume, causes mutual lock wait.
  
DATA OWNERSHIP CONFLICTS:
  - Product catalog: Oracle Billing is authoritative, but Amdocs maintains local copy (CUSTOMER_PRODUCT.PRODUCT_CODE)
  - Resource assignments: Netcracker is authoritative, but both Amdocs and Oracle maintain copies
  - Customer status: Amdocs is authoritative, but Oracle Billing has STATUS field that can diverge
*/

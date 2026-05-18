# SC Auditor Platform — Detailed Architecture

> **Status**: Brainstorming (Belum Eksekusi)
> **Dokumen Ini**: API Contracts, Event Schema, Database Schema per Service
> **Tanggal**: 17 Mei 2026

---

## Table of Contents

1. [API Contracts (gRPC Protobuf)](#1-api-contracts-grpc-protobuf)
2. [Event Schema (Message Queue)](#2-event-schema-message-queue)
3. [Database Schema per Service](#3-database-schema-per-service)
4. [End-to-End Pipeline Flow](#4-end-to-end-pipeline-flow)
5. [Immunefi Data Model](#5-immunefi-data-model)
6. [Proto File Structure](#6-proto-file-structure)
7. [Bug Classification System](#7-bug-classification-system)
8. [Matured Decisions](#8-matured-decisions)

---

## 1. API Contracts (gRPC Protobuf)

Setiap service mengekspos gRPC endpoint. REST gateway juga bisa di-generate dari proto yang sama.

### 1.1 Auth Service

```protobuf
syntax = "proto3";
package scauditor.auth.v1;

service AuthService {
  // User Management
  rpc CreateUser(CreateUserRequest) returns (CreateUserResponse);
  rpc GetUser(GetUserRequest) returns (User);
  rpc UpdateUser(UpdateUserRequest) returns (User);
  rpc DeleteUser(DeleteUserRequest) returns (Empty);

  // Authentication
  rpc Authenticate(AuthRequest) returns (AuthResponse);
  rpc ValidateToken(ValidateTokenRequest) returns (ValidateTokenResponse);
  rpc RefreshToken(RefreshTokenRequest) returns (AuthResponse);
  rpc RevokeToken(RevokeTokenRequest) returns (Empty);

  // API Keys
  rpc CreateApiKey(CreateApiKeyRequest) returns (ApiKey);
  rpc ListApiKeys(ListApiKeysRequest) returns (ListApiKeysResponse);
  rpc RevokeApiKey(RevokeApiKeyRequest) returns (Empty);

  // RBAC
  rpc AssignRole(AssignRoleRequest) returns (Empty);
  rpc CheckPermission(CheckPermissionRequest) returns (CheckPermissionResponse);
  rpc ListRoles(ListRolesRequest) returns (ListRolesResponse);
}

message User {
  string id = 1;
  string email = 2;
  string display_name = 3;
  repeated string roles = 4;
  bool email_verified = 5;
  int64 created_at = 6;
  int64 updated_at = 7;
}

message AuthRequest {
  string email = 1;
  string password_hash = 2;
  optional string mfa_code = 3;
}

message AuthResponse {
  string access_token = 1;
  string refresh_token = 2;
  int64 expires_at = 3;
  User user = 4;
}

message ValidateTokenRequest {
  string access_token = 1;
}

message ValidateTokenResponse {
  bool valid = 1;
  string user_id = 2;
  repeated string roles = 3;
  optional string error = 4;
}

message CheckPermissionRequest {
  string user_id = 1;
  string permission = 2;    // e.g., "project:create", "audit:start"
  optional string resource_id = 3;
}

message CheckPermissionResponse {
  bool allowed = 1;
}
```

### 1.2 Immunefi Scraper Service

```protobuf
syntax = "proto3";
package scauditor.immunefi.v1;

service ImmunefiScraperService {
  // Sync
  rpc TriggerSync(SyncTrigger) returns (SyncStatus);
  rpc GetSyncStatus(Empty) returns (SyncStatus);

  // Programs
  rpc ListPrograms(ListProgramsRequest) returns (ListProgramsResponse);
  rpc GetProgram(GetProgramRequest) returns (ImmunefiProgram);
  rpc SearchPrograms(SearchProgramsRequest) returns (ListProgramsResponse);

  // Contracts
  rpc ListContracts(ListContractsRequest) returns (ListContractsResponse);
  rpc GetContract(GetContractRequest) returns (ContractInfo);

  // Stats
  rpc GetStats(Empty) returns (ImmunefiStats);

  // Contracts pending audit
  rpc GetPendingContracts(PendingContractsRequest) returns (PendingContractsResponse);
}

service ImmunefiContractService {
  // Source code fetching
  rpc FetchSourceCode(FetchSourceRequest) returns (FetchSourceResponse);
  rpc GetCachedSource(GetSourceRequest) returns (SourceCode);
}

message ImmunefiProgram {
  string id = 1;
  string slug = 2;
  string name = 3;
  string logo_url = 4;
  string website = 5;
  // Bounty
  double max_bounty_usd = 6;
  string reward_type = 7;       // USDC, ETH, etc.
  bool kyc_required = 8;
  repeated string poc_required_for = 9;  // ["critical", "high", "medium"]
  // Scope
  repeated ContractAsset assets = 10;
  repeated string chains = 11;
  // Features
  repeated string features = 12;  // Managed Triage, Arbitration, etc.
  // Status
  string status = 13;           // active, paused, closed
  int64 added_at = 14;
  int64 last_updated = 15;
  // References
  repeated string previous_audits = 16;
  repeated string known_issues = 17;
  string safe_harbor = 18;
}

message ContractAsset {
  string address = 1;
  string chain = 2;
  string name = 3;
  string description = 4;
  string asset_type = 5;       // smart_contract, etc.
  string etherscan_url = 6;
  string source_type = 7;      // verified, unverified, proxy
  bool is_verified = 8;
}

message ImmunefiStats {
  int32 total_programs = 1;
  int32 active_programs = 2;
  int32 total_contracts = 3;
  double total_max_bounty = 4;
  // per chain
  map<string, int32> contracts_per_chain = 5;
  // top 10 by bounty
  repeated ImmunefiProgram top_programs = 6;
  int32 last_sync_at = 7;
}

message ListProgramsRequest {
  int32 page = 1;
  int32 page_size = 2;
  optional string sort_by = 3;     // bounty, name, updated
  optional string chain_filter = 4;
  optional string status_filter = 5;
  optional bool poc_required = 6;
}

message PendingContractsRequest {
  repeated string vulnerabilities = 1;  // prefer contracts with known vuln patterns
  double min_bounty = 2;
  repeated string chains = 3;
}
```

### 1.3 Orchestrator Service

```protobuf
syntax = "proto3";
package scauditor.orchestrator.v1;

service OrchestratorService {
  // Pipeline lifecycle
  rpc StartAudit(StartAuditRequest) returns (AuditSession);
  rpc GetAuditStatus(GetAuditRequest) returns (AuditSession);
  rpc CancelAudit(CancelAuditRequest) returns (Empty);
  rpc ListAudits(ListAuditsRequest) returns (ListAuditsResponse);

  // Pipeline management
  rpc GetPipelineDefinition(Empty) returns (PipelineDefinition);
  rpc UpdatePipelineConfig(UpdatePipelineConfigRequest) returns (PipelineDefinition);

  // Real-time progress
  rpc StreamAuditProgress(GetAuditRequest) returns (stream AuditEvent);
}

service SkillDispatchService {
  rpc DispatchSkills(DispatchRequest) returns (DispatchResponse);
  rpc GetSkillResult(GetSkillResultRequest) returns (SkillResult);
}

message StartAuditRequest {
  string project_id = 1;
  repeated string contract_ids = 2;    // contract addresses to audit
  string immunefi_program_id = 3;
  optional PipelineConfig config = 4;
}

message AuditSession {
  string session_id = 1;
  string project_id = 2;
  string immunefi_program_id = 3;
  AuditStatus status = 4;
  repeated PipelineStep steps = 5;
  int64 started_at = 6;
  optional int64 completed_at = 7;
  optional string error = 8;
}

message PipelineStep {
  string name = 1;           // static-analysis, exploit, ai-analysis, etc.
  StepStatus status = 2;     // pending, running, completed, failed, skipped
  optional int64 started_at = 3;
  optional int64 completed_at = 4;
  optional string result_ref = 5;   // reference to result data
  optional string error = 6;
}

message AuditEvent {
  string session_id = 1;
  string step = 2;
  string event_type = 3;     // started, progress, completed, failed
  string message = 4;
  int32 progress_pct = 5;
  optional string payload_json = 6;
}

message PipelineDefinition {
  repeated Stage stages = 1;
  int32 max_concurrent_scans = 2;
  bool auto_exploit = 3;
  bool auto_gas_analysis = 4;
  repeated string required_skills = 5;
}

message Stage {
  string name = 1;
  string service = 2;           // service to call
  repeated string depends_on = 3;  // stage names this depends on
  string timeout_seconds = 4;
  bool optional = 5;
}

enum AuditStatus {
  AUDIT_STATUS_UNSPECIFIED = 0;
  AUDIT_STATUS_PENDING = 1;
  AUDIT_STATUS_RUNNING = 2;
  AUDIT_STATUS_COMPLETED = 3;
  AUDIT_STATUS_FAILED = 4;
  AUDIT_STATUS_CANCELLED = 5;
}

enum StepStatus {
  STEP_STATUS_UNSPECIFIED = 0;
  STEP_STATUS_PENDING = 1;
  STEP_STATUS_RUNNING = 2;
  STEP_STATUS_COMPLETED = 3;
  STEP_STATUS_FAILED = 4;
  STEP_STATUS_SKIPPED = 5;
}
```

### 1.4 Static Analysis Service

```protobuf
syntax = "proto3";
package scauditor.static_analysis.v1;

service StaticAnalysisService {
  rpc RunScan(RunScanRequest) returns (ScanSession);
  rpc GetScanResult(GetScanRequest) returns (ScanResult);
  rpc ListScans(ListScansRequest) returns (ListScansResponse);
  rpc GetSupportedTools(Empty) returns (SupportedTools);
  rpc RunCustomTool(RunCustomToolRequest) returns (ScanSession);
}

message RunScanRequest {
  string source_url = 1;         // URL ke Storage Service
  string contract_address = 2;
  string chain = 3;
  repeated string tools = 4;     // ["slither", "mythril", "echidna"]
  optional string compiler_version = 5;
  optional map<string, string> tool_config = 6;
}

message ScanSession {
  string scan_id = 1;
  string status = 2;
  repeated string tools_running = 3;
  int64 started_at = 4;
}

message ScanResult {
  string scan_id = 1;
  string contract_address = 2;
  repeated Finding findings = 3;
  map<string, ToolOutput> tool_outputs = 4;
  int64 completed_at = 5;
  int32 duration_seconds = 6;
}

message Finding {
  string id = 1;
  string tool = 2;              // slither, mythril, echidna
  string title = 3;
  string description = 4;
  string severity = 5;          // critical, high, medium, low, informational
  double confidence = 6;        // 0.0 - 1.0
  string file = 7;
  int32 line_start = 8;
  int32 line_end = 9;
  string code_snippet = 10;
  string impact = 11;
  string recommendation = 12;
  repeated string references = 13;
  string swc_id = 14;           // SWC Registry ID
  string cwe_id = 15;           // CWE ID
}

message ToolOutput {
  string raw_output = 1;
  bool success = 2;
  optional string error = 3;
  int32 duration_seconds = 4;
}
```

### 1.5 Exploit Engine Service

```protobuf
syntax = "proto3";
package scauditor.exploit.v1;

service ExploitEngineService {
  rpc StartExploitSession(StartExploitRequest) returns (ExploitSession);
  rpc GetSessionStatus(GetExploitRequest) returns (ExploitSession);
  rpc ExecuteExploit(ExecuteExploitRequest) returns (ExploitResult);
  rpc StopExploit(StopExploitRequest) returns (Empty);
  rpc GetPoolStatus(Empty) returns (PoolStatus);
  rpc ListSessions(ListSessionsRequest) returns (ListSessionsResponse);
}

message StartExploitRequest {
  string contract_address = 1;
  string chain = 2;
  int32 fork_block = 3;          // block number to fork at
  string source_code_url = 4;
  repeated Vulnerability findings = 5;  // findings to test
  optional string rpc_endpoint = 6;     // archived node RPC
}

message ExploitSession {
  string session_id = 1;
  string status = 2;             // pending, forking, ready, executing, completed, failed
  string anvil_endpoint = 3;     // internal: http://anvil:8545
  int32 block_forked = 4;
  string chain_id = 5;
  int64 started_at = 6;
  PoolInstanceInfo instance = 7;
}

message ExecuteExploitRequest {
  string session_id = 1;
  string exploit_code = 2;       // Solidity/ethers.js exploit script
  repeated string accounts_to_impersonate = 3;
  optional uint64 eth_balance = 4;  // ETH to give impersonated account
  optional int32 gas_limit = 5;
}

message ExploitResult {
  string session_id = 1;
  bool exploit_successful = 2;
  string tx_hash = 3;
  string transaction_trace = 4;  // detailed trace
  int64 gas_used = 5;
  string state_diff = 6;         // state changes
  optional string error = 7;
  repeated ExploitAttempt attempts = 8;
}

message ExploitAttempt {
  int32 attempt_number = 1;
  string technique = 2;          // reentrancy, flash-loan, etc.
  bool success = 3;
  string result_summary = 4;
  int64 gas_used = 5;
}

message PoolInstanceInfo {
  string instance_id = 1;
  string container_id = 2;
  PoolStatus status = 3;
  int32 uptime_seconds = 4;
  int64 memory_used_mb = 5;
}
```

### 1.6 AI Analysis Service

```protobuf
syntax = "proto3";
package scauditor.ai.v1;

service AIAnalysisService {
  rpc AnalyzeVulnerabilities(AnalyzeRequest) returns (AnalyzeResponse);
  rpc GetAnalysisResult(GetAnalysisRequest) returns (AnalysisResult);
  rpc ReAnalyze(ReAnalyzeRequest) returns (AnalyzeResponse);
  rpc GenerateFixRecommendation(FixRequest) returns (FixResponse);
}

message AnalyzeRequest {
  string scan_id = 1;
  repeated StaticFinding scan_findings = 2;
  string source_code = 3;
  repeated PatternMatch pattern_matches = 4;
  optional AnalysisConfig config = 5;
}

message AnalysisResult {
  string analysis_id = 1;
  repeated AIVerdict verdicts = 2;
  string overall_assessment = 3;
  double risk_score = 4;        // 0-100
  string summary = 5;
  int64 processed_at = 6;
  string model_used = 7;
}

message AIVerdict {
  string finding_id = 1;
  bool confirmed = 2;
  double confidence = 3;        // 0.0 - 1.0
  string severity_reassessment = 4;  // up/down/same
  string reasoning = 5;
  optional string exploit_scenario = 6;
  optional string fix_recommendation = 7;
  double estimated_financial_impact = 8;  // USD if exploited
}

message FixRequest {
  string source_code = 1;
  string vulnerability_description = 2;
}

message FixResponse {
  string fixed_code = 1;
  string diff = 2;
  string explanation = 3;
  bool verified = 4;
}
```

### 1.7 Report Service

```protobuf
syntax = "proto3";
package scauditor.report.v1;

service ReportService {
  rpc GenerateReport(GenerateReportRequest) returns (Report);
  rpc GetReport(GetReportRequest) returns (Report);
  rpc ListReports(ReportsListRequest) returns (ListReportsResponse);
  rpc ExportReport(ExportReportRequest) returns (ExportResponse);
  rpc GetReportTemplate(GetTemplateRequest) returns (ReportTemplate);
  rpc ListTemplates(Empty) returns (ListTemplatesResponse);
}

message GenerateReportRequest {
  string audit_session_id = 1;
  string project_id = 2;
  string format = 3;              // pdf, html, md, json
  optional string template_id = 4;
  repeated string sections = 5;   // include only specific sections
}

message Report {
  string report_id = 1;
  string project_id = 2;
  string audit_session_id = 3;
  string title = 4;
  string format = 5;
  string immunefi_program_id = 6;
  // Sections
  string executive_summary = 7;
  repeated FindingReport findings = 8;
  double overall_score = 9;
  string risk_assessment = 10;
  string recommendations = 11;
  // Metadata
  int64 generated_at = 12;
  int32 total_findings = 13;
  int32 critical_count = 14;
  int32 high_count = 15;
  int32 medium_count = 16;
  int32 low_count = 17;
  optional string exported_url = 18;
}

message FindingReport {
  string id = 1;
  string title = 2;
  string severity = 3;
  string status = 4;           // confirmed, false_positive, unconfirmed
  string description = 5;
  string impact = 6;
  string exploit_scenario = 7;
  string proof_of_concept = 8;
  string recommendation = 9;
  string code_location = 10;
  string cwe_id = 11;
  double cvss_score = 12;
}

message ExportReportRequest {
  string report_id = 1;
  string format = 2;
}

message ExportResponse {
  string download_url = 1;
  int64 file_size_bytes = 2;
  string content_type = 3;
}
```

---

## 2. Event Schema (Message Queue)

Menggunakan **NATS** (JetStream) karena ringan dan persistent. Topics menggunakan format: `scauditor.{domain}.{event}`

### 2.1 Event Topics

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NATS JETSTREAM TOPICS                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  IMMUNEFI DOMAIN:                                                  │
│  ───────────────                                                   │
│  scauditor.immunefi.program.synced      → Program baru/update      │
│  scauditor.immunefi.contract.detected   → Contract baru in-scope   │
│  scauditor.immunefi.program.closed      → Program ditutup          │
│                                                                    │
│  PROJECT DOMAIN:                                                   │
│  ───────────────                                                   │
│  scauditor.project.created              → Project auto-created     │
│  scauditor.project.contracts_ready      → All contracts fetched    │
│  scauditor.project.updated              → Project status change    │
│                                                                    │
│  AUDIT DOMAIN:                                                     │
│  ────────────                                                      │
│  scauditor.audit.requested              → New audit requested      │
│  scauditor.audit.started                → Orchestrator mulai       │
│  scauditor.audit.step.completed         → Satu stage selesai       │
│  scauditor.audit.progress               → Progress update (N%)     │
│  scauditor.audit.completed              → Audit selesai            │
│  scauditor.audit.failed                 → Audit gagal              │
│  scauditor.audit.cancelled              → Audit dibatalkan         │
│                                                                    │
│  ANALYSIS DOMAIN:                                                  │
│  ───────────────                                                   │
│  scauditor.scan.completed               → Static scan selesai      │
│  scauditor.patterns.matched             → Vuln DB match selesai    │
│  scauditor.ai.analyzed                  → AI analysis selesai      │
│  scauditor.exploit.completed            → Exploit test selesai     │
│  scauditor.gas.analyzed                 → Gas analysis selesai     │
│  scauditor.skills.evaluated             → Skill eval selesai       │
│                                                                    │
│  REPORT DOMAIN:                                                    │
│  ─────────────                                                      │
│  scauditor.report.generated             → Report siap              │
│  scauditor.report.exported              → PDF/HTML exported        │
│                                                                    │
│  NOTIFICATION DOMAIN:                                              │
│  ──────────────────                                                │
│  scauditor.notification.sent            → Notif terkirim           │
│  scauditor.notification.failed          → Notif gagal              │
│                                                                    │
│  ERROR DOMAIN:                                                     │
│  ────────────                                                      │
│  scauditor.error.service_unavailable    → Service down             │
│  scauditor.error.pipeline_timeout       → Stage timeout            │
│  scauditor.error.dead_letter            → Unprocessable message    │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Event Message Format

Semua event menggunakan envelope format yang sama:

```json
{
  "id": "evt_abc123",
  "type": "scauditor.audit.step.completed",
  "source": "orchestrator-service",
  "correlation_id": "audit_sess_xyz789",
  "timestamp": 1717890123,
  "version": 1,
  "data": { /* per-event payload */ },
  "metadata": {
    "trace_id": "trace_xxx",
    "user_id": "user_abc",
    "project_id": "proj_123",
    "session_id": "audit_sess_xyz789",
    "service_version": "1.2.0"
  }
}
```

### 2.3 Key Event Payloads

**audit.requested** — Trigger pipeline dimulai
```json
{
  "type": "scauditor.audit.requested",
  "data": {
    "session_id": "audit_sess_xyz789",
    "project_id": "proj_123",
    "immunefi_program_id": "ethena",
    "contract_addresses": [
      "0x4c9edd5852cd905f086c759e8383e09bff1e68b3",
      "0x2b1d5c8b3e3d9f0a1c2b3d4e5f6a7b8c9d0e1f2a"
    ],
    "chain": "ethereum",
    "config": {
      "auto_exploit": true,
      "auto_gas_analysis": true,
      "include_skills": ["owasp", "reentrancy", "flash-loan"]
    },
    "max_bounty_usd": 3000000
  }
}
```

**scan.completed** — Static analysis selesai
```json
{
  "type": "scauditor.scan.completed",
  "data": {
    "scan_id": "scan_456",
    "session_id": "audit_sess_xyz789",
    "contract_address": "0x4c9edd5852cd905f086c759e8383e09bff1e68b3",
    "tools_run": ["slither", "mythril"],
    "findings_count": 5,
    "critical_count": 1,
    "high_count": 2,
    "medium_count": 1,
    "low_count": 1,
    "result_ref": "storage://scans/scan_456/result.json",
    "duration_seconds": 127
  }
}
```

**exploit.completed** — Exploit test selesai
```json
{
  "type": "scauditor.exploit.completed",
  "data": {
    "session_id": "exploit_sess_321",
    "audit_session_id": "audit_sess_xyz789",
    "vulnerability_tested": "Reentrancy in withdraw()",
    "exploit_successful": true,
    "tx_hash": "0xabcd...1234",
    "gas_used": 89432,
    "value_at_risk_usd": 1250000,
    "poC_available": true,
    "result_ref": "storage://exploits/exploit_321/result.json"
  }
}
```

### 2.4 Pipeline Orchestration Flow

```
NATS STREAMS: scauditor_audit_pipeline

[audit.requested] ────▶ Orchestrator memproses
       │
       ▼
[audit.started] ──────▶ Notifikasi ke WS/SSE
       │
       ▼  Dispatch ke Static Analysis Service
[scan.completed] ──────▶ Orchestrator mengecek
       │
       ├──▶ [patterns.matched] ──▶ Vuln DB matching
       │         │
       │         ▼
       │    [ai.analyzed] ──────▶ AI verdict
       │         │
       │         ▼
       │    [exploit.completed] ──▶ Jika confirm+berbahaya
       │         │
       │         ▼
       │    [gas.analyzed] ──────▶ Gas optimization
       │
       ▼
[report.generated] ────▶ Report Service kompilasi
       │
       ▼
[audit.completed] ──────▶ Delivery + notify user
```

---

## 3. Database Schema per Service

### 3.1 Auth Service — PostgreSQL

```sql
-- ============================================================
-- AUTH SERVICE: users, roles, api_keys, sessions
-- ============================================================

CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           VARCHAR(255) UNIQUE NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,
  display_name    VARCHAR(100) NOT NULL,
  email_verified  BOOLEAN DEFAULT false,
  mfa_enabled     BOOLEAN DEFAULT false,
  mfa_secret      VARCHAR(64),          -- encrypted TOTP secret
  avatar_url      TEXT,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now(),
  deleted_at      TIMESTAMPTZ           -- soft delete
);

CREATE TABLE roles (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(50) UNIQUE NOT NULL,  -- admin, hunter, viewer
  description     TEXT,
  is_system       BOOLEAN DEFAULT false,         -- cannot be deleted
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_roles (
  user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
  role_id         UUID REFERENCES roles(id) ON DELETE CASCADE,
  assigned_by     UUID REFERENCES users(id),
  assigned_at     TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE permissions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(100) UNIQUE NOT NULL,  -- project:create, audit:start
  description     TEXT,
  resource_type   VARCHAR(50)                    -- project, audit, report, etc.
);

CREATE TABLE role_permissions (
  role_id         UUID REFERENCES roles(id) ON DELETE CASCADE,
  permission_id   UUID REFERENCES permissions(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE api_keys (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
  name            VARCHAR(100) NOT NULL,
  key_hash        VARCHAR(255) NOT NULL,        -- hashed API key
  key_prefix      VARCHAR(8) NOT NULL,          -- first 8 chars for identification
  scopes          TEXT[] DEFAULT '{}',          -- array of permission names
  expires_at      TIMESTAMPTZ,
  last_used_at    TIMESTAMPTZ,
  is_revoked      BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
  refresh_token   VARCHAR(255) UNIQUE NOT NULL,
  ip_address      INET,
  user_agent      TEXT,
  expires_at      TIMESTAMPTZ NOT NULL,
  is_revoked      BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE audit_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id),
  action          VARCHAR(50) NOT NULL,         -- login, api_key_created, role_changed
  resource_type   VARCHAR(50),
  resource_id     VARCHAR(100),
  details         JSONB,
  ip_address      INET,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_api_keys_user ON api_keys(user_id) WHERE is_revoked = false;
CREATE INDEX idx_sessions_user ON sessions(user_id) WHERE is_revoked = false;
CREATE INDEX idx_audit_log_user ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action, created_at DESC);
```

### 3.2 Immunefi Scraper Service — PostgreSQL

```sql
-- ============================================================
-- IMMUNEFI SCRAPER SERVICE: programs, contracts, sync state
-- ============================================================

CREATE TABLE immunefi_programs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug            VARCHAR(100) UNIQUE NOT NULL,
  name            VARCHAR(255) NOT NULL,
  logo_url        TEXT,
  website         TEXT,
  -- Bounty info
  max_bounty_usd  NUMERIC(16, 2),
  reward_type     VARCHAR(20),                  -- USDC, ETH, etc.
  reward_details  JSONB,
  -- Requirements
  kyc_required    BOOLEAN DEFAULT false,
  poc_required    TEXT[] DEFAULT '{}',          -- severity levels requiring PoC
  -- Status
  status          VARCHAR(20) DEFAULT 'active', -- active, paused, closed
  -- Metadata
  added_at        TIMESTAMPTZ,
  last_updated    TIMESTAMPTZ,
  -- Features
  features        TEXT[] DEFAULT '{}',
  safe_harbor     TEXT,
  -- References
  previous_audits TEXT[] DEFAULT '{}',
  known_issues    TEXT[] DEFAULT '{}',
  -- Internal
  is_archived     BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT now(),
  synced_at       TIMESTAMPTZ
);

CREATE TABLE immunefi_contracts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  program_id      UUID REFERENCES immunefi_programs(id) ON DELETE CASCADE,
  address         VARCHAR(42) NOT NULL,         -- 0x...
  chain           VARCHAR(20) NOT NULL,         -- ethereum, arbitrum, etc.
  name            VARCHAR(255),
  description     TEXT,
  asset_type      VARCHAR(30) DEFAULT 'smart_contract',
  etherscan_url   TEXT,
  -- Source code status
  source_type     VARCHAR(20) DEFAULT 'unknown',-- verified, unverified, proxy, unknown
  is_verified     BOOLEAN DEFAULT false,
  -- Audit status
  audit_status    VARCHAR(20) DEFAULT 'pending',-- pending, scanning, done, error
  last_scan_id    UUID,
  -- Timestamps
  created_at      TIMESTAMPTZ DEFAULT now(),
  synced_at       TIMESTAMPTZ,
  -- Unique per chain+address
  UNIQUE (chain, address)
);

CREATE TABLE sync_history (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status          VARCHAR(20) NOT NULL,         -- running, completed, failed
  total_programs  INTEGER,
  updated_programs INTEGER,
  new_programs    INTEGER,
  closed_programs INTEGER,
  total_contracts INTEGER,
  new_contracts   INTEGER,
  error_message   TEXT,
  duration_ms     INTEGER,
  triggered_by    VARCHAR(50),                  -- cron, manual, webhook
  started_at      TIMESTAMPTZ NOT NULL,
  completed_at    TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_contracts_program ON immunefi_contracts(program_id);
CREATE INDEX idx_contracts_chain ON immunefi_contracts(chain);
CREATE INDEX idx_contracts_status ON immunefi_contracts(audit_status);
CREATE INDEX idx_programs_bounty ON immunefi_programs(max_bounty_usd DESC) WHERE status = 'active';
CREATE INDEX idx_programs_status ON immunefi_programs(status);
```

### 3.3 Project Service — PostgreSQL

```sql
-- ============================================================
-- PROJECT SERVICE: audit projects (auto-created from Immunefi)
-- ============================================================

CREATE TABLE projects (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  immunefi_program_id UUID REFERENCES immunefi_scraper.immunefi_programs(id),
  name            VARCHAR(255) NOT NULL,
  description     TEXT,
  chain           VARCHAR(20) NOT NULL,
  owner_id        UUID,                         -- user who owns this
  team_members    UUID[] DEFAULT '{}',          -- user IDs
  status          VARCHAR(20) DEFAULT 'active', -- active, archived, completed
  total_contracts INTEGER DEFAULT 0,
  scanned_contracts INTEGER DEFAULT 0,
  total_findings  INTEGER DEFAULT 0,
  critical_findings INTEGER DEFAULT 0,
  high_findings   INTEGER DEFAULT 0,
  overall_score   NUMERIC(4,1),                -- 0.0 - 10.0
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE project_contracts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
  contract_id     UUID REFERENCES immunefi_scraper.immunefi_contracts(id),
  address         VARCHAR(42) NOT NULL,
  chain           VARCHAR(20) NOT NULL,
  name            VARCHAR(255),
  audit_status    VARCHAR(20) DEFAULT 'pending',
  current_session_id UUID,
  scanned_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE (project_id, contract_id)
);

CREATE TABLE project_tags (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
  name            VARCHAR(50) NOT NULL,
  color           VARCHAR(7) DEFAULT '#6366f1',
  UNIQUE (project_id, name)
);

-- Indexes
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_immunefi ON projects(immunefi_program_id);
CREATE INDEX idx_project_contracts_status ON project_contracts(project_id, audit_status);
```

### 3.4 Static Analysis Service — PostgreSQL

```sql
-- ============================================================
-- STATIC ANALYSIS SERVICE: scans, findings, raw_outputs
-- ============================================================

CREATE TABLE scans (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      UUID,                         -- audit session ID
  contract_address VARCHAR(42) NOT NULL,
  chain           VARCHAR(20) NOT NULL,
  tools_used      TEXT[] NOT NULL,
  status          VARCHAR(20) DEFAULT 'pending',-- pending, running, completed, failed
  total_findings  INTEGER DEFAULT 0,
  critical_count  INTEGER DEFAULT 0,
  high_count      INTEGER DEFAULT 0,
  medium_count    INTEGER DEFAULT 0,
  low_count       INTEGER DEFAULT 0,
  source_url      TEXT,
  compiler_version VARCHAR(20),
  duration_seconds INTEGER,
  error_message   TEXT,
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scan_findings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id         UUID REFERENCES scans(id) ON DELETE CASCADE,
  tool            VARCHAR(30) NOT NULL,
  title           VARCHAR(255) NOT NULL,
  description     TEXT,
  severity        VARCHAR(20) NOT NULL,         -- critical, high, medium, low, info
  confidence      NUMERIC(3,2),                -- 0.00 - 1.00
  file            TEXT,
  line_start      INTEGER,
  line_end        INTEGER,
  code_snippet    TEXT,
  impact          TEXT,
  recommendation  TEXT,
  swc_id          VARCHAR(20),
  cwe_id          VARCHAR(20),
  references      TEXT[] DEFAULT '{}',
  ai_verdict      JSONB,                       -- from AI Analysis Service
  was_confirmed   BOOLEAN,                     -- AI confirmed?
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scan_tool_outputs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id         UUID REFERENCES scans(id) ON DELETE CASCADE,
  tool            VARCHAR(30) NOT NULL,
  raw_output      TEXT,
  success         BOOLEAN,
  error_message   TEXT,
  duration_seconds INTEGER,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_scans_session ON scans(session_id);
CREATE INDEX idx_scans_contract ON scans(contract_address);
CREATE INDEX idx_findings_scan ON scan_findings(scan_id);
CREATE INDEX idx_findings_severity ON scan_findings(scan_id, severity);
CREATE INDEX idx_findings_ai ON scan_findings(was_confirmed) WHERE was_confirmed IS NOT NULL;
```

### 3.5 Exploit Engine — No Persistent DB

Exploit Engine **tidak memiliki database persisten**. Semua state bersifat ephemeral.

Data yang perlu disimpan (oleh service lain):
- Exploit result → disimpan oleh **Storage Service** sebagai blob
- Exploit metadata → disimpan oleh **Report Service**
- Logs → stdout container, dikumpulkan oleh **Observability Stack**

### 3.6 AI Analysis Service — PostgreSQL + Vector

```sql
-- ============================================================
-- AI ANALYSIS SERVICE: predictions, embeddings, fix suggestions
-- ============================================================

CREATE TABLE ai_analyses (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id         UUID,
  session_id      UUID,
  contract_address VARCHAR(42),
  model_used      VARCHAR(50),                  -- gpt-4o, claude-4, deepseek-v4
  risk_score      NUMERIC(5,2),                -- 0.00 - 100.00
  overall_assessment TEXT,
  summary         TEXT,
  tokens_used     INTEGER,
  duration_ms     INTEGER,
  status          VARCHAR(20) DEFAULT 'completed',
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ai_verdicts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id     UUID REFERENCES ai_analyses(id) ON DELETE CASCADE,
  finding_id      UUID,
  confirmed       BOOLEAN,
  confidence      NUMERIC(3,2),
  severity_reassessment VARCHAR(20),
  reasoning       TEXT,
  exploit_scenario TEXT,
  estimated_impact_usd NUMERIC(16, 2),
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE fix_recommendations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id     UUID REFERENCES ai_analyses(id) ON DELETE CASCADE,
  finding_id      UUID,
  original_code   TEXT,
  fixed_code      TEXT,
  diff            TEXT,
  explanation     TEXT,
  gas_impact      VARCHAR(20),                 -- increase, decrease, neutral
  is_verified     BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Vector embeddings table (pgvector)
CREATE TABLE analysis_embeddings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id     UUID REFERENCES ai_analyses(id) ON DELETE CASCADE,
  content_type    VARCHAR(30),                 -- finding, fix, exploit
  content_hash    VARCHAR(64),
  embedding       VECTOR(1536),                -- OpenAI ada-3 dimensions
  metadata        JSONB,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ai_analyses_session ON ai_analyses(session_id);
CREATE INDEX idx_ai_verdicts_finding ON ai_verdicts(finding_id);
CREATE INDEX idx_embeddings_content ON analysis_embeddings USING ivfflat (embedding vector_cosine_ops);
```

### 3.7 Vulnerability DB Service — PostgreSQL + Redis

```sql
-- ============================================================
-- VULNERABILITY DB SERVICE: patterns, CVE, knowledge base
-- ============================================================

CREATE TABLE vuln_patterns (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(255) NOT NULL,
  category        VARCHAR(50) NOT NULL,        -- reentrancy, access-control, oracle, etc.
  severity        VARCHAR(20) NOT NULL,
  swc_id          VARCHAR(20),
  cwe_id          VARCHAR(20),
  description     TEXT NOT NULL,
  detection_rules JSONB,                       -- YARA-like rules for pattern matching
  code_example_bad TEXT,
  code_example_good TEXT,
  remediation     TEXT,
  references      TEXT[] DEFAULT '{}',
  is_active       BOOLEAN DEFAULT true,
  version         INTEGER DEFAULT 1,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cve_entries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cve_id          VARCHAR(20) UNIQUE NOT NULL, -- CVE-2024-12345
  title           VARCHAR(255) NOT NULL,
  description     TEXT,
  severity        VARCHAR(20),
  cvss_score      NUMERIC(3,1),
  affected_contracts TEXT[],
  affected_chains TEXT[],
  affected_versions TEXT[],
  exploit_available BOOLEAN DEFAULT false,
  exploit_ref     TEXT,
  fix_commit      TEXT,
  published_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE pattern_matches (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id         UUID,
  finding_id      UUID,
  pattern_id      UUID REFERENCES vuln_patterns(id),
  match_confidence NUMERIC(3,2),
  match_details   JSONB,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Redis cache: hot patterns, frequently matched
-- KEY: vuln:pattern:{id} → Pattern JSON
-- KEY: vuln:cve:{cve_id} → CVE JSON
-- KEY: vuln:hot_patterns → List of top-50 matched patterns (sorted set)

CREATE INDEX idx_vuln_patterns_category ON vuln_patterns(category);
CREATE INDEX idx_vuln_patterns_severity ON vuln_patterns(severity);
```

### 3.8 Report Service — PostgreSQL

```sql
-- ============================================================
-- REPORT SERVICE: reports, templates, exports
-- ============================================================

CREATE TABLE reports (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      UUID NOT NULL,
  project_id      UUID NOT NULL,
  immunefi_program_id VARCHAR(100),
  title           VARCHAR(255) NOT NULL,
  format          VARCHAR(10) NOT NULL,         -- pdf, html, md, json
  status          VARCHAR(20) DEFAULT 'draft',  -- draft, generated, exported
  -- Summary
  executive_summary TEXT,
  overall_score   NUMERIC(4,1),
  risk_assessment TEXT,
  recommendations TEXT,
  -- Counts
  total_findings  INTEGER DEFAULT 0,
  critical_count  INTEGER DEFAULT 0,
  high_count      INTEGER DEFAULT 0,
  medium_count    INTEGER DEFAULT 0,
  low_count       INTEGER DEFAULT 0,
  -- Export
  exported_url    TEXT,
  file_size_bytes INTEGER,
  generated_at    TIMESTAMPTZ DEFAULT now(),
  exported_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE report_findings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id       UUID REFERENCES reports(id) ON DELETE CASCADE,
  finding_ref     UUID,
  title           VARCHAR(255) NOT NULL,
  severity        VARCHAR(20) NOT NULL,
  status          VARCHAR(20) DEFAULT 'confirmed',
  description     TEXT,
  impact          TEXT,
  exploit_scenario TEXT,
  proof_of_concept TEXT,
  recommendation  TEXT,
  code_location   TEXT,
  cwe_id          VARCHAR(20),
  cvss_score      NUMERIC(3,1),
  sort_order      INTEGER,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE report_templates (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(100) NOT NULL,
  description     TEXT,
  format          VARCHAR(10) NOT NULL,
  template_body   TEXT NOT NULL,                -- Handlebars/MJML template
  is_default      BOOLEAN DEFAULT false,
  immunefi_compatible BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Insert default Immunefi-compatible template
INSERT INTO report_templates (name, description, format, template_body, is_default, immunefi_compatible)
VALUES (
  'Immunefi Standard',
  'Template sesuai format submission Immunefi bug bounty',
  'md',
  '# Vulnerability Report: {{program_name}}\n\n...',
  true,
  true
);

CREATE INDEX idx_reports_session ON reports(session_id);
CREATE INDEX idx_reports_project ON reports(project_id);
CREATE INDEX idx_reports_status ON reports(status);
```

### 3.9 Notification Service — PostgreSQL

```sql
-- ============================================================
-- NOTIFICATION SERVICE: webhooks, alerts, delivery logs
-- ============================================================

CREATE TABLE notification_templates (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(100) NOT NULL,
  event_type      VARCHAR(50) NOT NULL,         -- audit.completed, finding.critical, etc.
  channel         VARCHAR(20) NOT NULL,         -- email, slack, discord, webhook
  subject_template TEXT,
  body_template   TEXT,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE notification_queue (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type      VARCHAR(50) NOT NULL,
  channel         VARCHAR(20) NOT NULL,
  recipients      TEXT[],
  subject         TEXT,
  body            TEXT,
  status          VARCHAR(20) DEFAULT 'pending',-- pending, sent, failed
  retry_count     INTEGER DEFAULT 0,
  max_retries     INTEGER DEFAULT 3,
  last_error      TEXT,
  scheduled_at    TIMESTAMPTZ,
  sent_at         TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE webhooks (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID,
  name            VARCHAR(100),
  url             TEXT NOT NULL,
  secret          VARCHAR(255),                 -- for HMAC signing
  events          TEXT[] NOT NULL,              -- subscribe to specific events
  is_active       BOOLEAN DEFAULT true,
  last_triggered_at TIMESTAMPTZ,
  last_status_code INTEGER,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE delivery_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  notification_id UUID REFERENCES notification_queue(id),
  channel         VARCHAR(20),
  recipient       TEXT,
  status          VARCHAR(20),
  status_code     INTEGER,
  response_body   TEXT,
  duration_ms     INTEGER,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_notif_queue_status ON notification_queue(status, created_at);
CREATE INDEX idx_notif_queue_event ON notification_queue(event_type);
CREATE INDEX idx_webhooks_user ON webhooks(user_id);
```

---

## 4. End-to-End Pipeline Flow

### 4.1 Complete Audit Lifecycle

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                    FULL AUDIT PIPELINE — 8 Phases                              │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  PHASE 0: DISCOVERY (Immunefi Scraper)                                        │
│  ─────────────────────────────────────────                                     │
│  1. Cron trigger sync setiap 6 jam                                             │
│  2. Fetch projects.json dari GitHub (234+ programs)                            │
│  3. Diff dengan data existing → deteksi baru/update/closed                     │
│  4. Untuk program baru: fetch detail per program                              │
│  5. Simpan/update immunefi_programs + immunefi_contracts                      │
│  6. Emit: immunefi.program.synced                                             │
│                                                                                │
│  PHASE 1: AUTO-CREATE PROJECT (Project Service)                                │
│  ───────────────────────────────────────────────                               │
│  7. Project Service listens to immunefi.program.synced                        │
│  8. Untuk contract baru/terupdate: create project entry                        │
│  9. Fetch source code dari Etherscan (jika verified)                          │
│  10. Upload source ke Storage Service                                         │
│  11. Emit: project.contracts_ready                                            │
│                                                                                │
│  PHASE 2: AUDIT INITIATION (Orchestrator)                                      │
│  ──────────────────────────────────────────                                    │
│  12. Orchestrator listens to project.contracts_ready                          │
│  13. Prioritize berdasarkan: max_bounty, chain, new contracts                  │
│  14. Create AuditSession dengan pipeline config                               │
│  15. Emit: audit.requested → audit.started                                    │
│                                                                                │
│  PHASE 3: STATIC ANALYSIS                                                      │
│  ─────────────────────────                                                      │
│  16. Orchestrator dispatch ke Static Analysis Service                          │
│  17. Service pull source dari Storage Service                                  │
│  18. Run tools sesuai konfigurasi:                                             │
│      ├── Slither: control flow, inheritance, reentrancy                        │
│      ├── Mythril: symbolic execution, deeper paths                             │
│      └── Echidna: fuzzing, property testing                                   │
│  19. Parse semua output → unified finding format                               │
│  20. Simpan: scans + scan_findings + scan_tool_outputs                        │
│  21. Emit: scan.completed                                                     │
│                                                                                │
│  PHASE 4: PATTERN MATCHING (Vuln DB)                                           │
│  ──────────────────────────────────────                                        │
│  22. Vuln DB Service listens to scan.completed                                │
│  23. Match findings against vuln_patterns                                     │
│  24. Cross-reference dengan CVE entries                                       │
│  25. Hitung match_confidence                                                  │
│  26. Simpan: pattern_matches                                                  │
│  27. Emit: patterns.matched                                                   │
│                                                                                │
│  PHASE 5: AI ANALYSIS                                                          │
│  ────────────────────                                                          │
│  28. AI Analysis Service listens to patterns.matched                          │
│  29. Kirim findings + source code + pattern matches ke LLM                     │
│  30. Dapatkan:                                                                 │
│      ├── AI Verdict: confirmed/rejected tiap finding                          │
│      ├── Severity Reassessment: up/down/same                                  │
│      ├── Exploit Scenario: bagaimana exploit dilakukan                        │
│      ├── Fix Recommendation: kode perbaikan                                   │
│      └── Risk Score: 0-100                                                   │
│  31. Store: ai_analyses + ai_verdicts + fix_recommendations                   │
│  32. Generate embedding untuk future learning                                  │
│  33. Emit: ai.analyzed                                                        │
│                                                                                │
│  PHASE 6: EXPLOIT TESTING (Exploit Engine)                                     │
│  ──────────────────────────────────────────                                    │
│  34. Exploit Engine listens to ai.analyzed                                    │
│  35. Skip jika tidak ada finding critical/high yang confirmed                  │
│  36. Pool Manager: check available Anvil instance                              │
│  37. Spin up Anvil container:                                                  │
│      ├── --network=none                                                       │
│      ├── --load-mode=fork                                                     │
│      ├── --fork-url=<archived_rpc>                                           │
│      └── --fork-block-number=<block>                                         │
│  38. Execute exploit berdasarkan AI scenario:                                  │
│      ├── Impersonate accounts (owner, whale)                                  │
│      ├── Manipulate state (balance, storage, timestamp)                      │
│      └── Call vulnerable functions                                           │
│  39. Record: tx_hash, gas_used, state_diff, trace                             │
│  40. Jika berhasil: generate PoC script (Hardhat/Foundry format)             │
│  41. Simpan result → Storage Service                                          │
│  42. Destroy Anvil instance                                                   │
│  43. Emit: exploit.completed                                                  │
│                                                                                │
│  PHASE 7: GAS ANALYSIS (Gas Optimizer)                                        │
│  ────────────────────────────────────────                                     │
│  44. Gas Optimizer listens to ai.analyzed                                     │
│  45. Opcode-level profiling dari source code                                   │
│  46. Identifikasi gas-heavy patterns:                                          │
│      ├── Storage loops (SLOAD/GSSLOAD)                                       │
│      ├── Unbounded iterations                                                │
│      └── Inefficient data structures                                         │
│  47. Generate optimization suggestions                                         │
│  48. Simpan: gas_reports                                                      │
│  49. Emit: gas.analyzed (opsional, can be skipped)                            │
│                                                                                │
│  PHASE 8: REPORT GENERATION (Report Service)                                   │
│  ────────────────────────────────────────────                                 │
│  50. Report Service collects all events:                                       │
│      ├── scan.completed → findings                                           │
│      ├── patterns.matched → CVE refs                                        │
│      ├── ai.analyzed → verdicts + fixes                                     │
│      ├── exploit.completed → PoC                                            │
│      └── gas.analyzed → optimizations                                       │
│  51. Render sesuai template (Immunefi Standard)                               │
│  52. Generate PDF + HTML + Markdown                                           │
│  53. Hitung overall_score berdasarkan:                                        │
│      ├── (critical*10 + high*5 + medium*2) / total_contracts                │
│      ├── dikurangi jika exploit berhasil                                    │
│      └── ditambah jika AI confidence tinggi                                 │
│  54. Upload ke Storage Service                                                │
│  55. Emit: report.generated → audit.completed                                │
│                                                                                │
│  PHASE 9: DELIVERY (Notification Service)                                      │
│  ────────────────────────────────────────                                     │
│  56. Notification Service listens to audit.completed                          │
│  57. Send alerts sesuai konfigurasi:                                           │
│      ├── Email: ringkasan eksekutif + link report                            │
│      ├── Slack/Discord: critical findings summary                            │
│      └── Webhook: JSON payload untuk integrasi                              │
│  58. Update UI via WebSocket (real-time dari Phase 2-8)                       │
│  59. Log delivery ke delivery_logs                                            │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Time Estimation per Audit

```
TIME BREAKDOWN (target per contract):
───────────────────────────────────

  Discovery & Project Creation:     ~30 detik   (auto, no human)
  Source Code Fetch:               ~10 detik   (Etherscan API)
  Static Analysis (Slither):       ~60 detik   (quick pass)
  Static Analysis (Mythril):       ~5-30 menit (symbolic = heavy)
  Static Analysis (Echidna):       ~5-15 menit (fuzzing = time)
  Pattern Matching:                 ~5 detik   (DB lookup)
  AI Analysis:                     ~30 detik   (LLM inference)
  Exploit Testing:                 ~2-10 menit (Anvil + execution)
  Gas Analysis:                     ~20 detik   (opcode profiling)
  Report Generation:                ~10 detik   (template render)

  ─────────────────────────────────────────────────────
  TOTAL (1 contract, all tools):  ~15-60 menit
  TOTAL (1 contract, Slither only): ~3-5 menit

  SCALING:
  ├── 1 program (avg 5 contracts): ~1-5 jam
  ├── 10 programs:                 ~10-50 jam
  └── All 234+ programs:           ~1000+ jam (parallelize!)
```

---

## 5. Immunefi Data Model

### 5.1 GitHub Data Source

```
Source: https://raw.githubusercontent.com/infosec-us-team/
        Immunefi-Bug-Bounty-Programs-Unofficial/main/

├── projects.json           → Array program summaries
└── project/{slug}.json    → Detail per program (234+ files)
```

**projects.json structure:**
```json
{
  "id": "ethena",
  "name": "Ethena",
  "addedAt": 1717171200,
  "lastUpdated": 1717761375,
  "maxBounty": 3000000,
  "logoUrl": "https://..."
}
```

**project/{slug}.json structure (real example — Ethena):**
```json
{
  "project": "Ethena",
  "maxBounty": 3000000,
  "rewardType": "USDC",
  "kycRequired": true,
  "pocPerTypeAndSeverity": [
    "smart_contract - critical",
    "smart_contract - high",
    "smart_contract - medium"
  ],
  "assets": [
    {
      "url": "https://etherscan.io/address/0x4c9edd5852cd905f086c759e8383e09bff1e68b3",
      "type": "smart_contract",
      "description": "USDe.sol"
    }
  ],
  "features": ["Managed Triage", "Arbitration"],
  "safeHarbor": true,
  "previousAudits": [],
  "knownIssues": []
}
```

### 5.2 Sync Strategy

```
IMMUNEFI SCRAPER — SYNC STRATEGY
═══════════════════════════════════

 SCHEDULE:
  ├── Full sync: setiap 6 jam (cron)
  ├── Quick check: setiap 30 menit (HEAD request ke projects.json)
  └── On-demand: trigger manual dari UI/API

 PROCESS:
  1. GET projects.json → parse JSON
  2. Compare dengan immunefi_programs yang ada di DB
  3. Deteksi perubahan:
     ├── NEW: id tidak ada di DB → tambah
     ├── UPDATED: lastUpdated berbeda → fetch ulang
     └── REMOVED: ada di DB tapi tidak di remote → tandai closed
  4. Untuk setiap program baru/update:
     ├── GET project/{slug}.json
     ├── Parse assets → simpan contract addresses
     ├── Simpan metadata (bounty, KYC, PoC requirements)
     └── Emit event: immunefi.program.synced

 EDGE CASES:
  ├── Rate limiting: exponential backoff + jitter
  ├── Partial failure: simpan progress, retry yang gagal
  ├── Validation: skip entry tanpa contract address
  └── Dedup: address yang sama di multiple chains = contract berbeda
```

---

## 6. Proto File Structure

```
proto/
├── scauditor/
│   ├── auth/
│   │   └── v1/
│   │       └── auth.proto
│   ├── immunefi/
│   │   └── v1/
│   │       ├── immunefi.proto
│   │       └── source.proto
│   ├── orchestrator/
│   │   └── v1/
│   │       └── orchestrator.proto
│   ├── static_analysis/
│   │   └── v1/
│   │       └── analysis.proto
│   ├── exploit/
│   │   └── v1/
│   │       └── exploit.proto
│   ├── ai/
│   │   └── v1/
│   │       └── ai.proto
│   ├── vulndb/
│   │   └── v1/
│   │       └── vulndb.proto
│   ├── report/
│   │   └── v1/
│   │       └── report.proto
│   ├── storage/
│   │   └── v1/
│   │       └── storage.proto
│   ├── skill/
│   │   └── v1/
│   │       └── skill.proto
│   ├── gas/
│   │   └── v1/
│   │       └── gas.proto
│   └── notification/
│       └── v1/
│           └── notification.proto
├── common/
│   ├── v1/
│   │   ├── types.proto          # Shared types: Address, Chain, Finding, etc.
│   │   ├── events.proto         # Event envelope
│   │   └── pagination.proto     # Page/PageSize/PageToken
├── buf.yaml                     # Buf config for linting/breaking
├── buf.gen.yaml                 # Code generation config
└── README.md
```

---

## 7. Bug Classification System

### 7.1 The 4-Quadrant Detection Matrix

Setiap finding yang dihasilkan pipeline diklasifikasikan ke dalam 4 kategori untuk mengukur akurasi dan mendorong pembelajaran:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DETECTION MATRIX                                  │
│                     (Confusion Matrix)                               │
├─────────────────────────────┬───────────────────────────────────────┤
│                             │  ACTUAL VULNERABILITY                 │
│                             ├──────────────┬────────────────────────┤
│                             │  YES (Bug)   │  NO (No Bug)           │
├────────────┬────────────────┼──────────────┼────────────────────────┤
│ DETECTED   │ POSITIVE (P)   │  TRUE POS    │  FALSE POS             │
│ (Alat/     │                │  (TP)        │  (FP)                  │
│ AI bilang  │                │  ✅ Real bug │  ❌ False alarm        │
│ ada bug)   │                │  → Submit    │  → Catat, adjust       │
│            │                │  ke Immunefi │  → Kurangi confidence  │
│            ├────────────────┼──────────────┼────────────────────────┤
│            │ NEGATIVE (N)   │  FALSE NEG   │  TRUE NEG              │
│            │                │  (FN)        │  (TN)                  │
│            │                │  ⚠️ Missed!  │  ✅ Correctly safe     │
│            │                │  → Pelajaran  │  → Catat, naikkan      │
│            │                │    PALING     │    confidence pattern  │
│            │                │    PENTING    │                        │
└────────────┴────────────────┴──────────────┴────────────────────────┘
```

**Definisi untuk SC Auditor:**

| Klasifikasi | Definisi | Contoh | Action |
|-------------|----------|--------|--------|
| **True Positive (TP)** | Bug nyata, terkonfirmasi exploit atau AI + human | Reentrancy di withdraw(), terbukti bisa hack | ✅ Masuk laporan Immunefi |
| **False Positive (FP)** | Alat bilang ada bug, tapi setelah dicek aman | Slither detect "unused return" tapi safe | ❌ Dicatat, update pattern matching |
| **True Negative (TN)** | Alat bilang aman, dan memang aman | Function tanpa reentrancy path | ✅ Dicatat, confidence pattern naik |
| **False Negative (FN)** | Ada bug nyata tapi alat tidak detect | Oracle manipulation yang terlewat | ⚠️ PALING PENTING — trigger improvement cycle |

### 7.2 Finding Lifecycle & Reclassification

Setiap finding melewati stages yang bisa mengubah klasifikasinya:

```
FINDING LIFECYCLE:
═══════════════════════════════════════════════════════════════

STAGE 0: RAW (from Static Analysis)
  └── classification: unknown
  └── tool_severity: critical | high | medium | low | info
  └── confidence: 0.3 - 0.7 (tool-dependent)
       │
       ▼
STAGE 1: AI VERDICT (from AI Analysis Service)
  ├── AI classification: TP (confirmed) | FP (rejected)
  ├── AI confidence: 0.0 - 1.0
  └── Jika AI sangat yakin (confidence > 0.9) → langsung TP
       │
       ▼
STAGE 2: EXPLOIT TEST (from Exploit Engine) — only for critical/high TP
  ├── Exploit berhasil → classification = TP ✅ (confirmed)
  ├── Exploit gagal   → classification = FP ❌ (rejected)
  └── Jika gagal tapi AI high confidence → ⚠️ human review needed
       │
       ▼
STAGE 3: HUMAN REVIEW (from UI)
  ├── Human setujui AI → classification final
  └── Human koreksi    → classification berubah, update learning
       │
       ▼
STAGE 4: IMMUNEFI SUBMISSION (External Validation)
  ├── Immunefi accepted → ✅ TP confirmed final
  ├── Immunefi rejected → ❌ Ternyata FP, trigger reclassification
  └── Immunefi found additional bug → ⚠️ New FN, trigger improvement
       │
       ▼
STAGE 5: LEARNING LOOP (Feedback ke sistem)
  ├── TP → reinforce pattern, naikkan weight
  ├── FP → update filter, turunkan tool confidence
  ├── TN → naikkan confidence untuk pattern serupa
  └── FN → 🔴 KRITIS: buat pattern baru, update AI training
```

### 7.3 Database Model — Finding Classification

```sql
-- ============================================================
-- ADDITIONS TO Static Analysis Service Database
-- ============================================================

CREATE TYPE finding_classification AS ENUM (
  'unknown',
  'true_positive',
  'false_positive', 
  'true_negative',
  'false_negative'
);

CREATE TYPE classification_source AS ENUM (
  'tool_raw',
  'ai_verdict',
  'exploit',
  'human_review',
  'immunefi_feedback'
);

-- Add classification columns to scan_findings table
ALTER TABLE scan_findings ADD COLUMN classification finding_classification DEFAULT 'unknown';
ALTER TABLE scan_findings ADD COLUMN classification_confidence NUMERIC(3,2);
ALTER TABLE scan_findings ADD COLUMN classification_source classification_source;
ALTER TABLE scan_findings ADD COLUMN final_classification BOOLEAN DEFAULT false;

-- Reclassification history
CREATE TABLE finding_reclassifications (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id      UUID REFERENCES scan_findings(id) ON DELETE CASCADE,
  previous_class  finding_classification,
  new_class       finding_classification NOT NULL,
  source          classification_source NOT NULL,
  source_ref      VARCHAR(100),                 -- scan_id, analysis_id, exploit_id, user_id
  reasoning       TEXT,
  confidence      NUMERIC(3,2),
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- LEARNING METRICS SERVICE (new or part of Vuln DB)
-- ============================================================

CREATE TABLE platform_metrics (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_date     DATE NOT NULL,
  -- Counts
  total_findings  INTEGER DEFAULT 0,
  tp_count        INTEGER DEFAULT 0,
  fp_count        INTEGER DEFAULT 0,
  tn_count        INTEGER DEFAULT 0,
  fn_count        INTEGER DEFAULT 0,
  unclassified    INTEGER DEFAULT 0,
  -- Computed metrics
  precision       NUMERIC(5,4),                 -- TP / (TP + FP)
  recall          NUMERIC(5,4),                 -- TP / (TP + FN)
  f1_score        NUMERIC(5,4),                 -- 2 * (P * R) / (P + R)
  accuracy        NUMERIC(5,4),                 -- (TP + TN) / (TP + TN + FP + FN)
  false_positive_rate NUMERIC(5,4),            -- FP / (FP + TN)
  false_negative_rate NUMERIC(5,4),            -- FN / (FN + TP)
  -- Per tool
  tool_performance JSONB,                       -- {slither: {tp: 5, fp: 3, precision: 0.625}, ...}
  -- Per severity
  severity_breakdown JSONB,
  created_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE (metric_date)
);

CREATE TABLE learning_opportunities (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type            VARCHAR(20) NOT NULL,         -- fn, fp (FN = priority)
  finding_id      UUID REFERENCES scan_findings(id),
  description     TEXT NOT NULL,
  root_cause      TEXT,                         -- kenapa alat gagal detect / false alarm
  pattern_suggestion TEXT,                      -- proposed new pattern
  severity        VARCHAR(20),
  status          VARCHAR(20) DEFAULT 'open',   -- open, in_progress, resolved
  priority        INTEGER DEFAULT 0,            -- 0 (low) - 10 (critical)
  resolved_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_findings_class ON scan_findings(classification) WHERE final_classification = true;
CREATE INDEX idx_findings_reclass ON finding_reclassifications(finding_id, created_at DESC);
CREATE INDEX idx_learning_priority ON learning_opportunities(priority DESC) WHERE status = 'open';
CREATE INDEX idx_learning_type ON learning_opportunities(type) WHERE status = 'open';
```

### 7.4 Reporting Strategy — Dua Level Laporan

```
REPORT STRATEGY:
═══════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│ LAPORAN LEVEL 1: IMMUNEFI SUBMISSION                                │
│ ─────────────────────────────────────────────                       │
│ Tujuan: Submit bug bounty ke Immunefi                               │
│ Format: Markdown (template Immunefi Standard)                       │
│ Isi:    ✅ HANYA True Positives (confirmed)                         │
│         ✅ Exploit PoC (wajib untuk critical/high)                  │
│         ✅ Severity sesuai klasifikasi Immunefi                     │
│         ❌ TIDAK ada FP/TN/FN                                       │
│         ❌ TIDAK ada internal notes                                 │
│                                                                     │
│ Sections dalam Immunefi Report:                                     │
│ 1. Vulnerability Title                                              │
│ 2. Contract & Chain                                                 │
│ 3. Severity Classification                                          │
│ 4. Description & Impact                                             │
│ 5. Proof of Concept (Hardhat script)                                │
│ 6. Recommended Fix                                                  │
│ 7. References                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ LAPORAN LEVEL 2: INTERNAL AUDIT REPORT                              │
│ ───────────────────────────────────────                             │
│ Tujuan: Learning & improvement                                      │
│ Format: HTML/PDF/MD (detailed)                                      │
│ Isi:    ✅ Semua findings: TP + FP + TN + FN                        │
│         ✅ Classification confidence matrix                         │
│         ✅ Scoring & metrics (precision, recall, F1)                │
│         ✅ Per-tool performance breakdown                           │
│         ✅ Learning opportunities (FN analysis)                     │
│         ✅ Reclassification history                                 │
│                                                                     │
│ Sections dalam Internal Report:                                     │
│ 1. Executive Summary + Score                                        │
│ 2. Detection Matrix (4-quadrant chart)                              │
│ 3. True Positives (yang akan di-submit)                             │
│ 4. False Positives (yang ditolak AI/exploit)                        │
│ 5. False Negatives (⚠️ critical learning)                           │
│ 6. True Negatives (confirmed safe patterns)                         │
│ 7. Per-Tool Performance Analysis                                    │
│ 8. Learning Recommendations                                         │
│ 9. Full Finding Details (all classifications)                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.5 False Negative — Mekanisme Paling Kritis

FN adalah sinyal pembelajaran paling berharga. Platform harus proaktif mengejar FN:

```
FN DETECTION & RESPONSE:
═══════════════════════════════════════════════════════════════

 CARA FN TERDETEKSI:
  ├── 1. Immunefi Rejection dengan bug tambahan
  │    → Tim kami submit bug A (TP), Immunefi bilang "ada juga bug B"
  │    → Bug B adalah FN kami → catat, buat pattern
  │
  ├── 2. Known Issues dari Immunefi project page
  │    → Beberapa program punya known issues list
  │    → Cek apakah tool kami detect known issues = no? → FN
  │
  ├── 3. Cross-tool validation
  │    → Slither detect, Mythril tidak → Mythril mungkin FN
  │    → Evaluasi kenapa Mythril miss
  │
  ├── 4. Human peninjauan periodik
  │    → Sample audit: human audit manual sebagai benchmark
  │    → Bandingkan hasil → hitung FN rate
  │
  └── 5. Similar contract analysis
      → Contract A punya bug X, Contract B mirip
      → Apakah tool detect bug X di Contract B?
      → Jika tidak → FN pattern untuk contract serupa

 RESPONSE TERHADAP FN:
  ├── Priority: 10/10 (tertinggi)
  ├── Buat learning_opportunities entry dengan type='fn'
  ├── Analisis root cause: kenapa miss?
  │   ├── Tool limitation (Slither tidak check oracle)
  │   ├── Pattern tidak ada di Vuln DB
  │   ├── AI tidak trained untuk pattern ini
  │   └── Source code tidak ter-fetch (unverified contract)
  ├── Action:
  │   ├── Tambah pattern ke Vuln DB
  │   ├── Update AI prompt dengan contoh serupa
  │   └── Adjust tool configuration
  └── Verifikasi: re-run audit setelah improvement
```

### 7.6 Scoring System — Berbasis Confusion Matrix

Overall score menggunakan weighted formula yang mempertimbangkan TP, FP, dan FN:

```
SCORING FORMULA:
═══════════════════════════════════════════════════════════════

FINDING SCORE (per finding):
  base = severity_weight (critical=10, high=5, medium=2, low=1)
  
  IF classification = TP:
    IF exploit_successful → score = base × 1.5 (bonus exploit)
    ELSE → score = base × 1.0
  
  IF classification = FP:
    score = -(base × 0.3)  (penalty false alarm)
  
  IF classification = FN:
    score = -(base × 0.5)  (penalty missed bug — larger)
  
  IF classification = TN:
    score = +0.1            (small reward for correct safety)

OVERALL PROJECT SCORE:
  raw = SUM(all finding scores)
  max_possible = SUM(all severity_weights) × 1.5
  
  normalisasi: score = (raw / max_possible) × 10
  clamp: 0.0 - 10.0
  
  Grade:
  ├── 9.0 - 10.0 → S (Superior) — semua TP, exploit confirmed
  ├── 7.5 - 8.9  → A (Excellent) — TP dominan, sedikit FP
  ├── 5.0 - 7.4  → B (Good) — reasonable TP, beberapa FP
  ├── 3.0 - 4.9  → C (Fair) — terlalu banyak FP
  └── 0.0 - 2.9  → D (Poor) — dominan FP/FN, perlu review

PER-TOOL PRECISION (untuk evaluasi tool):
  precision = tool_TP / (tool_TP + tool_FP)
  
  Jika precision < 0.3 → tool perlu rekonfigurasi
  Jika precision > 0.9 → tool reliable, naikkan priority
```

---

## 8. Matured Decisions — 6 Item Final

### 8.1 Target Blockchain Pertama: EVM (Ethereum + EVM L2s)

**Keputusan**: EVM **wajib**, multi-chain **nanti**.

| Faktor | EVM | Solana | Other |
|--------|-----|--------|-------|
| Immunefi Coverage | ~90% program | ~5% | ~5% |
| Tool Maturity | Slither/Mythril/Echidna mature | Sedikit tools | Minimal |
| Anvil Support | ✅ Native fork | ❌ Tidak ada | ❌ |
| Skill Availability | Hermes EVM skills + Opencode SC Auditor | Limited | None |
| Complexity | Known | New paradigm (BPF) | Varied |

```
ROADMAP CHAIN SUPPORT:
═══════════════════════════════════════════════════════════════

Fase 1 (Launch):    Ethereum + Arbitrum + Optimism + Base + Polygon
                    → Semua EVM, reuse Slither/Mythril/Echidna

Fase 2 (Q3 2026):   BNB Chain + Avalanche + Fantom + Mantle
                    → Masih EVM, tambah RPC endpoints

Fase 3 (Q4 2026):   Solana + Near
                    → Butuh tool baru (Not right now)
```

### 8.2 Exploit Engine Stack: TypeScript (utama) + Python (Hermes Scripts)

**Keputusan**: **TypeScript** untuk 95% Exploit Engine, **Python** hanya untuk Hermes skill scripting.

| Komponen | Stack | Alasan |
|----------|-------|--------|
| API Layer (gRPC/REST) | TypeScript | Satu ekosistem dengan service lain, proto shared |
| Pool Manager | TypeScript (Dockerode) | Cukup untuk initial, worker_threads untuk concurrency |
| Anvil Lifecycle | TypeScript (child_process) | Spawn/kill Anvil process |
| Exploit Execution | TypeScript (ethers.js v6) | Hardhat-native, ethers.js mature |
| PoC Generation | TypeScript (Handlebars) | Template-based PoC script generation |
| Hermes Exploit Scripts | Python | Panggil Hermes via subprocess/gRPC untuk pattern tertentu |

```
type ExploitEngine struct {
  api: Express/Fastify        → TypeScript
  pool: ContainerManager      → TypeScript (Dockerode)
  executor: TransactionEngine → TypeScript (ethers.js)
  hermes: HermesBridge        → Python (subprocess)
}
```

**Tidak pakai Go** — alasan: menambah bahasa = menambah kompleksitas build system, CI/CD, debugging. Go bisa ditambahkan nanti jika pool management butuh performa ribuan container concurrent.

### 8.3 Deduplikasi Skill: 109 → ~20 Core Skills

**Keputusan**: Adaptasi **15-20 skills** dari 109 total. Sisanya tidak relevan untuk audit platform.

```
SKILL DEDUP STRATEGY:
═══════════════════════════════════════════════════════════════

 SUMBER: 109 skills
  ├── Hermes: 43 primary + 18 optional = 61
  ├── Paperclip: 8
  └── Opencode: 58 (32 built-in + 26 custom)
       │
       ▼
 FILTER 1: RELEVANSI
  └── Hanya skill yang relevan untuk smart contract audit
       │
       ▼
 FILTER 2: DEDUP
  └── Skill serupa dari multiple framework → merge, pilih terbaik
       │
       ▼
 HASIL: ~20 Core Skills

 # | Skill | Sumber | Kegunaan dalam Platform
---|-------|--------|------------------------|
 1 | smartcontract-auditor | Opencode | Main audit framework |
 2 | blockchain-evm | Hermes | EVM analysis patterns |
 3 | red-teaming-godmode | Hermes | Exploit generation patterns |
 4 | security-sherlock | Hermes | DeFi security patterns |
 5 | security-oss-forensics | Hermes | On-chain forensics |
 6 | database-security | Opencode | Secure data handling |
 7 | reentrancy-detector | (custom) | Reentrancy-specific analysis |
 8 | oracle-manipulation | (custom) | Oracle manipulation patterns |
 9 | access-control | (custom) | Access control analysis |
10 | flash-loan-attacks | (custom) | Flash loan attack vectors |
11 | systematic-debugging | Hermes | Debugging methodology |
12 | test-driven-development | Hermes | Test writing |
13 | implementation-planning | Hermes | Task planning |
14 | agent-driven-development | Hermes | Sub-agent patterns |
15 | understanding | Opencode | Context analysis |
16 | workflow-general | Opencode | Pipeline workflow |
17 | app-quality | Opencode | Quality scoring |
18 | prompt-engineering | Opencode | AI prompt optimization |
19 | self-improving-skills | Opencode | Continuous learning |
20 | plugin-sdk | Paperclip | Extension system |

CATATAN: 
- Skill Hermes dan Opencode adalah MARKDOWN — bisa di-parse oleh service manapun
- Tidak perlu adaptasi kode, cukup format ulang untuk Skill Service
- Skills baru akan ditambahkan seiring pembelajaran dari FN
```

### 8.4 Build Priority: 4 Waves, Parallel dalam Wave

**Keputusan**: 4 waves, service dalam wave yang sama dikerjakan PARALEL.

```
BUILD WAVES:
═══════════════════════════════════════════════════════════════

WAVE 1 — FOUNDATION (Minggu 1-2)
  Tujuan: Data masuk, user bisa login, project tercreate
  Parallel: ✅ Semua service di wave 1 independen
  
  ├── Immunefi Scraper    → sync 234+ programs, contract addresses
  ├── Auth Service        → users, JWT, RBAC, API keys
  ├── Storage Service     → MinIO, source code storage
  └── Project Service     → auto-create dari Immunefi data
       │
       ▼ Dependency for next wave: project with contracts + source code
       ▼

WAVE 2 — CORE AUDIT (Minggu 3-5)
  Tujuan: Pipeline audit dasar berfungsi
  Sequential: Orchestrator → Static → VulnDB → AI (dependent chain)
  
  ├── Orchestrator Service    → pipeline engine, event-driven
  ├── Static Analysis Service → Slither/Mythril/Echidna
  ├── Vuln DB Service         → pattern matching
  └── AI Analysis Service     → LLM verdict, severity scoring
       │
       ▼ Dependency: AI verdict + pattern match → Exploit Engine
       ▼

WAVE 3 — ADVANCED (Minggu 6-8)
  Tujuan: Exploit, gas, skill integration
  Parallel: Exploit & Gas independen, Skill tergantung hasil
  
  ├── Exploit Engine        → Anvil fork, PoC generation
  ├── Gas Optimizer Service → opcode-level gas analysis
  └── Skill Service         → Hermes/Opencode skill integration
       │
       ▼ Dependency: all results → Report Service
       ▼

WAVE 4 — DELIVERY (Minggu 9-10)
  Tujuan: Report, notification, UI, gateway
  Parallel: ✅ Semua independen
  
  ├── Report Service        → TP/FP/TN/FN report generation
  ├── Notification Service  → webhook, email, Slack
  ├── API Gateway           → Kong/Envoy routing
  └── UI                    → React dashboard (dari Paperclip)
```

### 8.5 Deployment Model: Hybrid (VPS + Local Dev)

**Keputusan**: **Hybrid** — VPS untuk services, local untuk Exploit Engine development.

```
DEPLOYMENT ARCHITECTURE:
═══════════════════════════════════════════════════════════════

                    ┌──────────────────────┐
                    │    DEVELOPMENT        │
                    │  (Local Machine)     │
                    │                      │
                    │  • Docker Compose    │
                    │  • Semua service     │
                    │  • Anvil testnet     │
                    │  • Hot reload        │
                    └──────────────────────┘
                            │
                            ▼ (deploy via CI/CD)
                    ┌──────────────────────┐
                    │    PRODUCTION         │
                    │  (VPS: Hetzner CX22)  │
                    │  ≈ €8-12 / bulan      │
                    │                      │
                    │  • Docker Compose    │
                    │  • 14 containers     │
                    │  • NATS JetStream    │
                    │  • MinIO storage     │
                    │                      │
                    │  SPECS:              │
                    │  ├── 2 vCPU          │
                    │  ├── 4 GB RAM        │
                    │  ├── 80 GB SSD       │
                    │  └── 1 Gbpsネット    │
                    └──────────────────────┘
                            │
                            ▼ (on-demand)
                    ┌──────────────────────┐
                    │    EXPLOIT ENGINE     │
                    │  (Scale to Zero)      │
                    │                      │
                    │  • Anvil containers  │
                    │  • --network=none    │
                    │  • tmpfs RAM disk    │
                    │  • Spin up only saat │
                    │    exploit dibutuhkan │
                    │  • Auto-destroy      │
                    └──────────────────────┘

 WHY VPS BUKAN FULL CLOUD:
  ├── Biaya: VPS €8-12 vs Cloud $50-100/bulan
  ├── Anvil butuh akses Docker socket → VPS lebih mudah
  └── Kompleksitas: Kubernetes overkill untuk personal platform

 WHY VPS BUKAN LOCAL ONLY:
  ├── Immunefi scraper harus jalan 24/7
  ├── Cron sync tidak bisa di laptop mati
  └── API endpoint harus selalu available
```

### 8.6 Nama Platform — Options & Rekomendasi

**Keputusan**: Belum final — 5 opsi diajukan, user pilih:

```
CANDIDATE NAMES:
═══════════════════════════════════════════════════════════════

1. ⭐ VYPER              → "Vyper" = cepat + "VIPER" = ular berbisa
                          → Cepat mendeteksi, berbisa ke bug
                          → branding: "Vyper - Smart Contract Hunter"
                          → Domain: vyper.dev ✅ available

2.   SENTRY              → Penjaga, pengawas
                          → branding: "Sentry - Immunefi Bug Hunter"
                          → Domain: sentry.dev ❌ taken

3.   FORGE               → Tempa, forge (cocok dengan Foundry)
                          → branding: "Forge - Automated Audit Platform"
                          → Domain: forge.dev ❌ probably taken

4.   ECHIDNA             → Nama tool fuzzing, tapi bisa ambigu
                          → branding: "Echidna - Smart Contract Security"
                          → Domain: echidna.dev ❌ taken

5.   CRAWLER             → Crawl (merayap) mencari bug
                          → branding: "Crawler - Bug Bounty Automator"
                          → Domain: crawler.dev ✅ available

REKOMENDASI: VYPER
  ├── Short (5 huruf) — mudah diingat
  ├── Unik — tidak bentrok dengan tool terkenal
  ├── Metafora kuat: ular berbisa → bisa mendeteksi + menyerang bug
  ├── .dev domain available
  └── Bisa dikembangkan: "VyperScan", "VyperAudit", "VyperChain"
```

---

> **Dokumen ini adalah arsitektur detail dari SC Auditor Platform.**
> API contracts, event schema, database schema, bug classification, dan matured decisions siap untuk implementasi.
> Semua service wajib dibangun — tidak ada yang opsional.
>
> *Generated by lore-master — 17 Mei 2026*

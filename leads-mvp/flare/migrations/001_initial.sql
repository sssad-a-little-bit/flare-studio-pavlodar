CREATE TABLE sources (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
);
CREATE TABLE businesses (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, normalized_name TEXT NOT NULL,
 category TEXT NOT NULL, city TEXT NOT NULL, address TEXT NOT NULL DEFAULT '',
 website TEXT, website_status TEXT NOT NULL DEFAULT 'unchecked'
   CHECK(website_status IN ('found','not_found','unchecked','ambiguous')),
 website_checked_at TEXT, website_check_source TEXT,
 stage TEXT NOT NULL DEFAULT 'новый' CHECK(stage IN
 ('новый','требует проверки','готов к звонку','связались','заинтересован','отказ','перезвонить','клиент','исключён')),
 do_not_contact INTEGER NOT NULL DEFAULT 0 CHECK(do_not_contact IN (0,1)),
 exclusion_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE identities (
 kind TEXT NOT NULL, value TEXT NOT NULL, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
 PRIMARY KEY(kind,value)
);
CREATE INDEX identities_business ON identities(business_id);
CREATE TABLE evidence (
 id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
 source_id INTEGER NOT NULL REFERENCES sources(id), url TEXT NOT NULL,
 observed_at TEXT NOT NULL, excerpt TEXT NOT NULL CHECK(length(excerpt)<=600),
 confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1), fingerprint TEXT NOT NULL UNIQUE
);
CREATE TABLE observations (
 id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
 evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, payload TEXT NOT NULL, observed_at TEXT NOT NULL,
 fingerprint TEXT NOT NULL UNIQUE
);
CREATE INDEX observations_business ON observations(business_id,kind,observed_at);
CREATE TABLE contacts (
 id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, value TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'business',
 verified INTEGER NOT NULL DEFAULT 0, evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
 UNIQUE(business_id,kind,value,role)
);
CREATE TABLE collection_attempts (
 id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(id),
 city TEXT NOT NULL, category TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
 status TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0, error_code TEXT
);
CREATE TABLE interactions (
 id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
 occurred_at TEXT NOT NULL, kind TEXT NOT NULL, outcome TEXT NOT NULL, note TEXT NOT NULL DEFAULT ''
);
-- Только SHA-256 идентификаторов удалённых обработанных записей: без контактов.
CREATE TABLE suppressions (
 digest TEXT PRIMARY KEY, do_not_contact INTEGER NOT NULL, reason TEXT NOT NULL
);

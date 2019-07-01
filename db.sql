
---
create table api_cache (
    id integer primary key autoincrement,
    parameter TEXT,
    method TEXT,
    result TEXT,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

create index api_cache_idx_method ON api_cache (method);
create index api_cache_idx_parameter ON api_cache (parameter);
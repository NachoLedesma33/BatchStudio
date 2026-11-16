-- 002_search.sql
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    doc_id UNINDEXED,
    session_id UNINDEXED,
    page_no UNINDEXED,
    name,
    content
);

CREATE TABLE research_results(run_id TEXT NOT NULL,symbol TEXT NOT NULL,strategy_id TEXT NOT NULL,strategy_version TEXT NOT NULL,created_at REAL NOT NULL,metrics TEXT NOT NULL,PRIMARY KEY(run_id,symbol,strategy_id,strategy_version));
INSERT INTO research_results VALUES('run-a','BTCUSDT','historical.alpha','1',123.5,'{"net": 1.20, "legacy": NaN}');
INSERT INTO research_results VALUES('run-b','ETHUSDT','historical.beta','2',1e999,'not-json: original metrics TEXT');

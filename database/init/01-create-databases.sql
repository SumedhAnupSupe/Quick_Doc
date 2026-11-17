-- Local development only. Creates isolated databases + least-privilege roles so the Central Vault
-- and the Maharashtra State Vault have separate access boundaries from the operational database.
-- The passwords below are throwaway development values, not production credentials.
CREATE ROLE nexus LOGIN PASSWORD 'nexus_dev_pw';
CREATE ROLE central_vault LOGIN PASSWORD 'central_dev_pw';
CREATE ROLE state_vault LOGIN PASSWORD 'state_dev_pw';

CREATE DATABASE apaar_nexus OWNER nexus;
CREATE DATABASE apaar_central_vault OWNER central_vault;
CREATE DATABASE apaar_state_mh_vault OWNER state_vault;

REVOKE ALL ON DATABASE apaar_central_vault FROM PUBLIC;
REVOKE ALL ON DATABASE apaar_state_mh_vault FROM PUBLIC;
REVOKE ALL ON DATABASE apaar_nexus FROM PUBLIC;

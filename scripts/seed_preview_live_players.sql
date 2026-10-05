-- PREVIEW ONLY: project mqnrrlymoddxgnyadsvy.
-- Run in a transaction after:
-- SET LOCAL flagtastic.preview_seed = 'mqnrrlymoddxgnyadsvy';
-- Never run as a schema migration or against production.
DO $seed$
DECLARE
    team_record RECORD;
    missing INTEGER;
    jersey INTEGER;
    new_player INTEGER;
    player_age INTEGER;
    dob DATE;
    test_identity TEXT;
BEGIN
    IF current_setting('flagtastic.preview_seed', true) IS DISTINCT FROM 'mqnrrlymoddxgnyadsvy' THEN
        RAISE EXCEPTION 'Explicit preview seed marker is required';
    END IF;
    LOCK TABLE teams, players, team_players IN SHARE ROW EXCLUSIVE MODE;
    FOR team_record IN SELECT id, category FROM teams ORDER BY id LOOP
        SELECT GREATEST(0, 7 - count(*))::INTEGER INTO missing
        FROM team_players WHERE team_id = team_record.id AND active;
        player_age := CASE lower(team_record.category)
            WHEN 'u6' THEN 5 WHEN 'u8' THEN 7 WHEN 'u10' THEN 9
            WHEN 'u12' THEN 11 WHEN 'u14' THEN 13 WHEN 'u16' THEN 15
            WHEN 'u18' THEN 17 ELSE 20 END;
        dob := make_date(extract(year FROM current_date)::INTEGER - player_age, 1, 1);
        WHILE missing > 0 LOOP
            SELECT candidate INTO jersey FROM generate_series(1, 99) candidate
            WHERE NOT EXISTS (
                SELECT 1 FROM team_players
                WHERE team_id = team_record.id AND jersey_number = candidate
            ) ORDER BY candidate LIMIT 1;
            IF jersey IS NULL THEN
                RAISE EXCEPTION 'No available jersey for team %', team_record.id;
            END IF;
            test_identity := 'TEST-' || team_record.id || '-' || jersey;
            INSERT INTO players (name, aka, curp, age, identity_type, birth_date)
            VALUES ('Jugador de prueba T' || team_record.id || ' #' || jersey,
                    'Prueba #' || jersey, test_identity, player_age, 'provisional', dob)
            ON CONFLICT (curp) DO NOTHING RETURNING id INTO new_player;
            IF new_player IS NULL THEN
                SELECT id INTO new_player FROM players WHERE curp = test_identity;
            END IF;
            INSERT INTO team_players (team_id, player_id, jersey_number, active)
            VALUES (team_record.id, new_player, jersey, true);
            missing := missing - 1;
        END LOOP;
    END LOOP;
END
$seed$;

-- Corrected f1 schema
-- Generated at 2025-08-12T06:08:00

CREATE DATABASE IF NOT EXISTS `f1` DEFAULT CHARACTER SET utf8mb4;
USE `f1`;

-- circuits
DROP TABLE IF EXISTS circuits;
CREATE TABLE circuits (
    circuit_id INT(11),
    circuit_ref VARCHAR(255),
    name VARCHAR(255),
    location VARCHAR(255),
    country VARCHAR(255),
    lat FLOAT,
    lng FLOAT,
    alt INT(11),
    url VARCHAR(255)
);
-- constructor_results
DROP TABLE IF EXISTS constructor_results;
CREATE TABLE constructor_results (
    constructor_results_id INT(11),
    race_id INT(11),
    constructor_id INT(11),
    points FLOAT,
    status VARCHAR(255)
);
-- constructor_standings
DROP TABLE IF EXISTS constructor_standings;
CREATE TABLE constructor_standings (
    constructor_standings_id INT(11),
    race_id INT(11),
    constructor_id INT(11),
    points FLOAT,
    position INT(11),
    position_text VARCHAR(255),
    wins INT(11)
);
-- constructors
DROP TABLE IF EXISTS constructors;
CREATE TABLE constructors (
    constructor_id INT(11),
    constructor_ref VARCHAR(255),
    name VARCHAR(255),
    nationality VARCHAR(255),
    url VARCHAR(255)
);
-- driver_standings
DROP TABLE IF EXISTS driver_standings;
CREATE TABLE driver_standings (
    driver_standings_id INT(11),
    race_id INT(11),
    driver_id INT(11),
    points FLOAT,
    position INT(11),
    position_text VARCHAR(255),
    wins INT(11)
);
-- drivers
DROP TABLE IF EXISTS drivers;
CREATE TABLE drivers (
    driver_id INT(11),
    driver_ref VARCHAR(255),
    number INT(11),
    code VARCHAR(3),
    forename VARCHAR(255),
    surname VARCHAR(255),
    dob DATE,
    nationality VARCHAR(255),
    url VARCHAR(255)
);
-- lap_times
DROP TABLE IF EXISTS lap_times;
CREATE TABLE lap_times (
    race_id INT(11),
    driver_id INT(11),
    lap INT(11),
    position INT(11),
    time VARCHAR(255),
    milliseconds INT(11)
);
-- pit_stops
DROP TABLE IF EXISTS pit_stops;
CREATE TABLE pit_stops (
    race_id INT(11),
    driver_id INT(11),
    stop INT(11),
    lap INT(11),
    time TIME,
    duration VARCHAR(255),
    milliseconds INT(11)
);
-- qualifying
DROP TABLE IF EXISTS qualifying;
CREATE TABLE qualifying (
    qualify_id INT(11),
    race_id INT(11),
    driver_id INT(11),
    constructor_id INT(11),
    number INT(11),
    position INT(11),
    q1 VARCHAR(255),
    q2 VARCHAR(255),
    q3 VARCHAR(255)
);
-- races
DROP TABLE IF EXISTS races;
CREATE TABLE races (
    race_id INT(11),
    year INT(11),
    round INT(11),
    circuit_id INT(11),
    name VARCHAR(255),
    date DATE,
    time TIME,
    url VARCHAR(255),
    fp1_date VARCHAR(255),
    fp1_time VARCHAR(255),
    fp2_date VARCHAR(255),
    fp2_time VARCHAR(255),
    fp3_date VARCHAR(255),
    fp3_time VARCHAR(255),
    quali_date VARCHAR(255),
    quali_time VARCHAR(255),
    sprint_date VARCHAR(255),
    sprint_time VARCHAR(255)
);
-- results
DROP TABLE IF EXISTS results;
CREATE TABLE results (
    result_id INT(11),
    race_id INT(11),
    driver_id INT(11),
    constructor_id INT(11),
    number INT(11),
    grid INT(11),
    position INT(11),
    position_text VARCHAR(255),
    position_order INT(11),
    points FLOAT,
    laps INT(11),
    time VARCHAR(255),
    milliseconds INT(11),
    fastest_lap INT(11),
    `rank` INT(11),
    fastest_lap_time VARCHAR(255),
    fastest_lap_speed VARCHAR(255),
    status_id INT(11)
);
-- seasons
DROP TABLE IF EXISTS seasons;
CREATE TABLE seasons (
    year INT(11),
    url VARCHAR(255)
);
-- status
DROP TABLE IF EXISTS status;
CREATE TABLE status (
    status_id INT(11),
    status VARCHAR(255)
);
-- sprint_results
DROP TABLE IF EXISTS sprint_results;
CREATE TABLE sprint_results (
    result_id INT(11),
    race_id INT(11),
    driver_id INT(11),
    constructor_id INT(11),
    number INT(11),
    grid INT(11),
    position INT(11),
    position_text VARCHAR(255),
    position_order INT(11),
    points FLOAT,
    laps INT(11),
    time VARCHAR(255),
    milliseconds INT(11),
    fastest_lap INT(11),
    fastest_lap_time VARCHAR(255),
    fastest_lap_speed VARCHAR(255),
    status_id INT(11)
);
-- short_grand_prix_names
DROP TABLE IF EXISTS short_grand_prix_names;
CREATE TABLE short_grand_prix_names (
    full_name VARCHAR(255),
    short_name VARCHAR(255)
);
-- short_constructor_names
DROP TABLE IF EXISTS short_constructor_names;
CREATE TABLE short_constructor_names (
    constructor_ref VARCHAR(255),
    short_name VARCHAR(255)
);
-- liveries
DROP TABLE IF EXISTS liveries;
CREATE TABLE liveries (
    constructor_ref VARCHAR(255),
    start_year INT(11),
    end_year INT(11),
    primary_hex_code VARCHAR(255)
);
-- tdr_overrides
DROP TABLE IF EXISTS tdr_overrides;
CREATE TABLE tdr_overrides (
    year INT(11),
    constructor_ref VARCHAR(255),
    driver_ref VARCHAR(255),
    team_driver_rank INT(11)
);
-- circuits_ext
DROP TABLE IF EXISTS circuits_ext;
CREATE TABLE circuits_ext (
    circuit_id INT,
    circuit_ref TEXT,
    name TEXT,
    location TEXT,
    country TEXT,
    lat REAL,
    lng REAL,
    alt INT,
    url TEXT,
    last_race_year  INT,
    number_of_races  INT
);
-- constructors_ext
DROP TABLE IF EXISTS constructors_ext;
CREATE TABLE constructors_ext (
    constructor_id INT,
    constructor_ref TEXT,
    name TEXT,
    nationality TEXT,
    url TEXT,
    short_name  VARCHAR(64)
);
-- drivers_ext
DROP TABLE IF EXISTS drivers_ext;
CREATE TABLE drivers_ext (
    driver_id INT,
    driver_ref TEXT,
    number INT,
    code  VARCHAR(8),
    forename TEXT,
    surname TEXT,
    full_name TEXT,
    dob DATE,
    nationality TEXT,
    url TEXT
);
-- driver_standings_ext
DROP TABLE IF EXISTS driver_standings_ext;
CREATE TABLE driver_standings_ext (
    driver_standings_id INT,
    race_id INT,
    driver_id INT,
    points REAL,
    position INT,
    position_text TEXT,
    wins INT
);
-- lap_times_ext
DROP TABLE IF EXISTS lap_times_ext;
CREATE TABLE lap_times_ext (
    race_id INT,
    driver_id INT,
    lap INT,
    position INT,
    time TEXT,
    milliseconds INT,
    seconds REAL,
    running_milliseconds  INT
);
-- lap_time_stats
DROP TABLE IF EXISTS lap_time_stats;
CREATE TABLE lap_time_stats (
    race_id INT,
    driver_id INT,
    avg_milliseconds  INT,
    avg_seconds  DECIMAL(10,3),
    stdev_milliseconds  INT,
    stdev_seconds  DECIMAL(10,3)
);
-- races_ext
DROP TABLE IF EXISTS races_ext;
CREATE TABLE races_ext (
    race_id INT,
    year INT,
    round INT,
    circuit_id INT,
    name TEXT,
    date DATE,
    time TIME,
    url TEXT,
    fp1_date TEXT,
    fp1_time TEXT,
    fp2_date TEXT,
    fp2_time TEXT,
    fp3_date TEXT,
    fp3_time TEXT,
    quali_date TEXT,
    quali_time TEXT,
    sprint_date TEXT,
    sprint_time TEXT,
    is_pit_data_available  TINYINT(1),
    short_name  VARCHAR(64),
    has_sprint  TINYINT(1),
    max_points  DECIMAL(6,2)
);
-- team_driver_ranks
DROP TABLE IF EXISTS team_driver_ranks;
CREATE TABLE team_driver_ranks (
    year INT,
    constructor_id INT,
    constructor_ref TEXT,
    driver_id INT,
    driver_ref TEXT,
    team_driver_rank  INT
);
-- drives
DROP TABLE IF EXISTS drives;
CREATE TABLE drives (
    year INT,
    driver_id INT,
    drive_id  INT,
    constructor_id INT,
    first_round INT,
    last_round INT,
    is_first_drive_of_season  TINYINT(1),
    is_final_drive_of_season  TINYINT(1)
);
-- retirements
DROP TABLE IF EXISTS retirements;
CREATE TABLE retirements (
    race_id INT,
    driver_id INT,
    lap  INT,
    position_order INT,
    status_id INT,
    retirement_type  VARCHAR(255)
);
-- lap_positions
DROP TABLE IF EXISTS lap_positions;
CREATE TABLE lap_positions (
    race_id INT,
    driver_id INT,
    lap INT,
    position INT,
    lap_type  VARCHAR(32)
);

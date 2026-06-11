# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
payload = '''
-- Drop and recreate seed tables

DROP TABLE IF EXISTS students CASCADE;
CREATE TABLE students (
    badge_id    VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(100),
    department  VARCHAR(100),
    year_or_sem INTEGER
);

INSERT INTO students (badge_id, name, department, year_or_sem) VALUES
('BADGE000001', 'Alice Johnson',    'Engineering', 1),
('BADGE000002', 'Bob Smith',        'Science',     2),
('BADGE000003', 'Carol White',      'Business',    3),
('BADGE000004', 'David Brown',      'Arts',        4),
('BADGE000005', 'Emma Davis',       'Medicine',    1),
('BADGE000006', 'Frank Miller',     'Law',         2),
('BADGE000007', 'Grace Wilson',     'Engineering', 3),
('BADGE000008', 'Henry Moore',      'Science',     4),
('BADGE000009', 'Iris Taylor',      'Business',    1),
('BADGE000010', 'Jack Anderson',    'Arts',        2),
('BADGE000011', 'Kate Thomas',      'Medicine',    3),
('BADGE000012', 'Liam Jackson',     'Law',         4),
('BADGE000013', 'Mia Harris',       'Engineering', 1),
('BADGE000014', 'Noah Martin',      'Science',     2),
('BADGE000015', 'Olivia Garcia',    'Business',    3),
('BADGE000016', 'Peter Martinez',   'Arts',        4),
('BADGE000017', 'Quinn Robinson',   'Medicine',    1),
('BADGE000018', 'Rachel Clark',     'Law',         2),
('BADGE000019', 'Sam Rodriguez',    'Engineering', 3),
('BADGE000020', 'Tina Lewis',       'Science',     4);

DROP TABLE IF EXISTS teachers CASCADE;
CREATE TABLE teachers (
    badge_id    VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(100),
    department  VARCHAR(100)
);

INSERT INTO teachers (badge_id, name, department) VALUES
('TEACHER00001', 'Dr. Alan Grant',    'Engineering'),
('TEACHER00002', 'Dr. Ellie Sattler', 'Science'),
('TEACHER00003', 'Dr. Ian Malcolm',   'Business'),
('TEACHER00004', 'Dr. John Hammond',  'Arts'),
('TEACHER00005', 'Dr. Sarah Harding', 'Medicine'),
('TEACHER00006', 'Dr. Robert Burke',  'Law'),
('TEACHER00007', 'Dr. Paul Kirby',    'Engineering'),
('TEACHER00008', 'Dr. Amanda Kirby',  'Science'),
('TEACHER00009', 'Dr. Billy Brennan', 'Business'),
('TEACHER00010', 'Dr. Eric Kirby',    'Arts');
'''

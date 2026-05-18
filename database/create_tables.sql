DROP TABLE IF EXISTS meal_items CASCADE;
DROP TABLE IF EXISTS meals CASCADE;
DROP TABLE IF EXISTS daily_logs CASCADE;
DROP TABLE IF EXISTS product_categories CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS category CASCADE;
DROP TABLE IF EXISTS plan_schedule CASCADE;
DROP TABLE IF EXISTS user_plans CASCADE;
DROP TABLE IF EXISTS meal_plans CASCADE;
DROP TABLE IF EXISTS meal_types CASCADE;
DROP TABLE IF EXISTS users CASCADE;
--таблица пользователей

CREATE TABLE Users(
	user_id serial not null primary key,
	login varchar(255) not null unique,
	password_hash VARCHAR(255) not null,
	gender char(10) check (gender in ('мужской', 'женский')),
	weight numeric check (weight>0),
	height integer check(height>0 and height<250),
	age integer check (age>0),
	goal_type varchar(16) check (goal_type in ('поддержание', 'похудение', 'набор')),
	target_weight decimal(5, 2) check (target_weight > 0),
	target_calories integer,
	is_folowing_plan boolean default false
);


CREATE TABLE Category(
	category_id serial primary key,
	name varchar(100) not null unique
);

CREATE TABLE Products(
	product_id serial primary key,
	name varchar(150) not null,
	calories_per_100_g DECIMAL(6,2) not null check (calories_per_100_g >= 0),
	proteins_per_100_g DECIMAL(6,2) not null check (proteins_per_100_g >= 0),
	fats_per_100_g DECIMAL(6,2) not null check (fats_per_100_g >= 0),
	carbs_per_100_g DECIMAL(6,2) not null check (carbs_per_100_g >= 0)
);

CREATE TABLE Product_categories(
	product_id integer REFERENCES Products(product_id),
	category_id integer REFERENCES Category(category_id),
	PRIMARY KEY(product_id, category_id)
);

CREATE TABLE Meal_types(
	meal_type_id serial primary key,
	name varchar(10) not null unique
);

CREATE TABLE Daily_logs( --сводка за день
	log_id serial primary key,
	user_id integer not null,
	log_date date not null,
	total_calories DECIMAL(6,2) not null default 0,
	total_proteins DECIMAL(6,2) not null default 0,
	total_fats DECIMAL(6,2) not null default 0,
	total_carbs DECIMAL(6,2) not null default 0,
	FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
	CONSTRAINT uq_daily_log_user_date UNIQUE (user_id, log_date)
);

CREATE TABLE Meals(
	meal_id serial primary key,
	log_id integer not null,
	meal_type_id integer not null,
	FOREIGN KEY (log_id) REFERENCES Daily_logs(log_id) ON DELETE CASCADE,
	FOREIGN KEY (meal_type_id) REFERENCES Meal_types(meal_type_id) ON DELETE Restrict,
	UNIQUE(log_id, meal_type_id)
);


CREATE TABLE Meal_items(
	item_id serial primary key not null,
	meal_id integer not null,
	product_id integer not null,
	weight_grams numeric not null check (weight_grams>=0) default 0,
	calories numeric not null default 0,
	proteins numeric not null default 0,
	fats numeric not null default 0,
	carbs numeric not null default 0,
	FOREIGN KEY (meal_id) REFERENCES Meals(meal_id) ON DELETE CASCADE,
	Foreign KEY (product_id) REFERENCES Products(product_id) ON DELETE RESTRICT
);


CREATE TABLE Meal_Plans (
    plan_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    target_calories integer NOT NULL,
    target_proteins DECIMAL(6,2),
    target_fats DECIMAL(6,2),
    target_carbs DECIMAL(6,2),
    duration_days INT DEFAULT 7,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE User_Plans (
    user_id INT PRIMARY KEY REFERENCES Users(user_id) ON DELETE CASCADE,
    plan_id INT REFERENCES Meal_Plans(plan_id),
    start_date DATE DEFAULT CURRENT_DATE,
    current_day_index INT DEFAULT 1 
);

CREATE TABLE Plan_Schedule (
    schedule_id SERIAL PRIMARY KEY,
    plan_id INT REFERENCES Meal_Plans(plan_id) ON DELETE CASCADE,
    day_index INT CHECK (day_index BETWEEN 1 AND 7), 
    meal_type_id INT REFERENCES Meal_Types(meal_type_id),
    product_id INT REFERENCES Products(product_id),
    recommended_weight_g DECIMAL(6,2) NOT NULL,
    UNIQUE(plan_id, day_index, meal_type_id, product_id)
);
CREATE TABLE User_Weight_Log (
    log_id serial primary key,
    user_id integer REFERENCES Users(user_id) ON DELETE CASCADE,
    log_date date NOT NULL DEFAULT CURRENT_DATE,
    weight_kg DECIMAL(5,2) NOT NULL CHECK (weight_kg > 20 AND weight_kg < 300)
);
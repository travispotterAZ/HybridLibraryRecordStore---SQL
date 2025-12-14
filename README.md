# Hybrid Library Record Store

A SQLite-based vinyl record library management system with user authentication, loan/purchase workflows, and database performance analysis.

## Project Structure

- **sql/** — Database schema, seed data, and workflow SQL scripts
- **src/** — Python scripts for user interactions and experiments
- **data/** — SQLite databases and CSV record data
- **Data Sourcing/** — Scripts to generate records.csv from Spotify API
- **docs/** — Analysis reports and experimental findings

## Database

The system uses a SQLite database (`data/main.db`) with the following core tables:

- **Users** — User accounts with authentication
- **Artists** — Music artists and genres
- **Records** — Vinyl records in the collection
- **Copies** — Physical copies of records
- **Loans** — Temporary record checkouts (7-day loans)
- **Orders** — Record purchases
- **Carts** — User shopping carts

## Data Source: records.csv

The file `data/records.csv` contains 1,844 vinyl records (artists, titles, genres, release dates) sourced from the **Spotify API**. 

**Generated using:** [Data Sourcing/](Data%20Sourcing/) scripts
- `main.py` — Queries Spotify for artists by genre
- `spotify/client.py` — Spotify API authentication
- `spotify/fetch.py` — Album/record retrieval logic
- `records.py` — Record data parsing
- `export.py` — Export to CSV format

The CSV columns are:
```
record_id, artist_id, title, release_date, total_tracks, artist_genre, artist_name
```

Note: `record_id` defaults to `-1` as a placeholder; the actual IDs are assigned when records are inserted into the database.

## Scripts in `src/`

Run scripts from the project root directory. All scripts connect to `data/main.db` by default.

### User Management

**`register_user.py`**
```bash
python src/register_user.py
```
Interactive script to register a new user account. Prompts for username, email, and password.

### Catalog Search

**`search_collection.py`**
```bash
python src/search_collection.py
```
Browse and search the vinyl record collection by artist, title, or genre.

### Checkout Workflows

**`loan_checkout.py`**
```bash
python src/loan_checkout.py
```
Checkout a record for a 7-day loan. Requires a user ID and record ID.

**`loan_return.py`**
```bash
python src/loan_return.py
```
Return a loaned record. Updates the loan return timestamp and copy status.

**`buy_checkout.py`**
```bash
python src/buy_checkout.py
```
Purchase records from cart and complete the order.

**`add_to_cart.py`**
```bash
python src/add_to_cart.py
```
Add records to your shopping cart.

**`view_cart.py`**
```bash
python src/view_cart.py
```
Display your current shopping cart contents.

**`view_orders.py`**
```bash
python src/view_orders.py
```
Display your order history.


## Setup & Initialization

1. **Create the database schema:**
   ```bash
   sqlite3 data/main.db < sql/schemas.sql
   ```

2. **Seed initial data:**
   ```bash
   sqlite3 data/main.db < sql/seed.sql
   ```

3. **Create performance indexes:**
   ```bash
   sqlite3 data/main.db < sql/create_indexes.sql
   ```

4. **Load records from CSV (optional):**
   ```bash
   sqlite3 data/main.db < sql/insert.sql
   ```


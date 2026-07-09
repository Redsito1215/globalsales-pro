# API Contracts: Plataforma Web GLOBTRADE

Base prefix for application endpoints: `/api`

## Shared Authentication

### POST `/api/auth/register`

Creates an account. The first user may become administrator; subsequent users are
analysts unless changed by project logic.

**Body**: `email`, `password`, `password_confirm`, `name`

**Success**: `201` with `status`, `message`, `user`

### POST `/api/auth/login`

Starts a session.

**Body**: `email` or `username`, `password`

**Success**: `200` with `status`, `message`, `user`

### POST `/api/auth/logout`

Clears the session.

**Success**: `200` with `status`, `message`

### GET `/api/auth/me`

Returns current authentication state.

**Success**: `200` with `authenticated` and `user`

## Q1 Tablero

### GET `/api/summary`

Returns dashboard KPIs. Public read.

**Query**: `region`, `item_type`, `channel`, `priority`, `months`

### GET `/api/regions`, `/api/products`, `/api/trend`, `/api/channels`, `/api/priorities`, `/api/countries`

Returns chart datasets. Public read.

**Query**: common filters; `/trend` accepts `months`; `/countries` accepts `top`.

### GET `/api/orders`

Returns paginated sales records. Public read.

**Query**: `country`, `item_type`, `channel`, `priority`, `region`, `limit`, `offset`

### GET `/api/orders/count`

Returns count for the current sales filters. Public read.

### POST `/api/sales_records/generate`

Generates sales records. Administrator required.

**Body**: `count`

## Q3 Ventas

### GET `/api/sales/orders`

Returns paginated order list for the Ventas page. Public read.

**Query**: `country`, `item_type`, `channel`, `priority`, `region`, `limit`, `offset`

### GET `/api/sales/orders/{order_id}`

Returns order detail. Public read.

### POST `/api/sales/orders`

Creates an order. Administrator required.

### PUT `/api/sales/orders/{order_id}`

Updates an order. Administrator required.

### DELETE `/api/sales/orders/{order_id}`

Deletes an order. Administrator required.

## Q2 Analisis

### GET `/api/analysis/trend`

Returns trend analysis dataset. Public read.

### GET `/api/analysis/regions`

Returns region and country analysis dataset. Public read.

### GET `/api/analysis/products`

Returns product analysis dataset. Public read.

### GET `/api/analysis/export`

Exports analysis data. Authenticated analyst or administrator required.

## Q4 Datos

### GET `/api/master/tables`

Lists available master/dimensional collections. Public read.

### GET `/api/master/{name}`

Returns paginated rows for a master table. Public read.

**Query**: `limit`, `offset`, optional text search if implemented.

### GET `/api/schema`

Returns schema/model summary cards. Public read.

### POST `/api/build_model`

Runs model build or dimensional transformation. Administrator required.

### POST `/api/load_dataset`

Runs dataset load. Administrator required.

### GET `/api/elt_status`

Returns current data/ELT status. Public read.

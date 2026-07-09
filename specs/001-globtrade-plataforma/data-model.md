# Data Model: Plataforma Web GLOBTRADE

## SalesRecord

Represents one sales order in `sales_records`.

**Fields**:
- `order_id`: unique business identifier.
- `region`, `country`: geographic classification.
- `item_type`: product category/type.
- `sales_channel`: sales channel.
- `order_priority`: priority value.
- `order_date`, `ship_date`: date strings used by filters and trends.
- `units_sold`: quantity sold.
- `unit_price`, `unit_cost`: pricing inputs.
- `total_revenue`, `total_cost`, `total_profit`: computed commercial metrics.

**Relationships**:
- Referenced by dashboard, analysis, and sales views.
- Aggregated by region, country, channel, priority, product, and month.

**Validation Rules**:
- `order_id` must be present for detail/update/delete.
- Numeric values must be non-negative.
- Date fields must support chronological filtering.

## User

Represents an authenticated account in the users collection managed by
`backend/auth/users.py`.

**Fields**:
- `id` or Mongo `_id`: stable identifier.
- `email`: unique login identifier.
- `name`: display name.
- `password_hash`: stored credential hash.
- `role`: `analista` or `administrador`.
- `active`: whether the account can log in.

**Relationships**:
- Session stores public user id, email, name, and role.
- Role controls write/export/load permissions.

**Validation Rules**:
- Email must be normalized.
- Password must pass validators before account creation.
- First registered user may become administrator; later users default to analyst unless changed.

## Role

Represents allowed capability groups.

**Values**:
- `visitante`: unauthenticated read-only behavior.
- `analista`: authenticated read plus export/analysis capabilities when enabled.
- `administrador`: all analyst capabilities plus generate/build/load/CRUD actions.

## MasterTable

Represents a readable dimensional collection in MongoDB.

**Fields**:
- `name`: collection name, usually `dim_*`.
- `display_name`: Spanish label for UI.
- `fields`: visible columns.
- `records`: paginated result set.

**Relationships**:
- Used by Q4 Datos master table browser and schema cards.

## FilterSelection

Represents UI-selected criteria for dashboard, analysis, and sales lists.

**Fields**:
- `region`
- `item_type`
- `channel`
- `priority`
- `country`
- `months`
- `limit`
- `offset`

**Validation Rules**:
- Empty filters are treated as no filter.
- `months=999` means all historical data.
- Pagination limits must stay within UI-defined options.

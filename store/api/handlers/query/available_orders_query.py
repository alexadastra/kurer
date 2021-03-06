from sqlalchemy import and_, func, select
from sqlalchemy.orm import join

from store.db.schema import orders_table, delivery_hours_table, orders_delivery_hours_table, couriers_working_hours_table, working_hours_table


AVAILABLE_ORDERS_QUERY = select(
    [
        orders_table.c.order_id,
        orders_table.c.courier_id,
        orders_table.c.weight,
        orders_table.c.region,
        func.array_remove(
            func.array_agg(delivery_hours_table.c.time_start),
            None
        ).label('time_start'),
        func.array_remove(
            func.array_agg(delivery_hours_table.c.time_finish),
            None
        ).label('time_finish'),
    ]
).select_from(
    orders_table.outerjoin(
        orders_delivery_hours_table.join(
            delivery_hours_table,
            orders_delivery_hours_table.c.delivery_hours_id == delivery_hours_table.c.delivery_hours_id
        ), orders_table.c.order_id == orders_delivery_hours_table.c.order_id
    )
).group_by(
    orders_table.c.order_id
)

from datetime import date

from marshmallow import Schema, ValidationError, validates, validates_schema
from marshmallow.fields import Date, Dict, Float, Int, List, Nested, Str
from marshmallow.validate import Length, OneOf, Range

from store.db.schema import CourierType
import re


class CouriersNested(Nested):
    def _deserialize(self, *args, **kwargs):
        try:
            return super()._deserialize(*args, **kwargs)
        except ValidationError as err:
            err.messages = {'validation_error': {'couriers': [{'id': i} for i in err.messages]}}
            raise err


class OrdersNested(Nested):
    def _deserialize(self, *args, **kwargs):
        try:
            return super()._deserialize(*args, **kwargs)
        except ValidationError as err:
            err.messages = {'validation_error': {'orders': [{'id': i} for i in err.messages]}}
            raise err


def validate_time_mark(time_mark, value_title, i):
    hours, minutes = int(time_mark.split(":")[0]), int(time_mark.split(":")[0])
    if hours > 23:
        raise ValidationError(
            'incorrect value for {} on index {}. {} is out of range'.format(value_title, i, hours)
        )
    if minutes > 59:
        raise ValidationError(
            'incorrect value for {} on index {}. {} is out of range'.format(value_title, i, minutes)
        )
    return hours, minutes


class PostRequestSchema(Schema):
    data = Nested(CouriersNested)

    @validates_schema
    def validate_unique_courier_id(self, data, **_):
        courier_ids_set = set()
        couriers_ids_list = list()
        for courier in data['data']:
            courier_ids_set.add(courier['courier_id'])
            couriers_ids_list.append(courier['courier_id'])
        if len(couriers_ids_list) != len(courier_ids_set):
            raise ValidationError(
                {'data': {'validation_error': [
                    {'id': i
                     } for i in [item for item in courier_ids_set if couriers_ids_list.count(item) > 1]
                ]}})


def validate_hour_intervals_list(hour_intervals_list, value_title):
    for i in range(len(hour_intervals_list)):
        hour_interval = hour_intervals_list[i]
        time_start, time_finish = hour_interval.split("-")
        # check if time interval isn't empty
        if time_start == time_finish:
            raise ValidationError(
                'time interval {} is empty'.format(hour_interval)
            )
        # check if time mark is correct (hours are in [0..23], minutes are in [0..59])
        hours_start, minutes_start = validate_time_mark(time_start, value_title, i)
        hours_finish, minutes_finish = validate_time_mark(time_finish, value_title, i)
        # should we check "23:00"-"2:00" or "23:00"-"0:00"? yes indeed
        if hours_start * 60 + minutes_start > hours_finish * 60 + minutes_finish:
            raise ValidationError(
                'time_start ({}) is greater than time_finish ({}).'.format(time_start, time_finish)
            )


def validate_hour_intervals_with_regular_expressions(hour_intervals_list, value_title):
    pattern = re.compile('^\d\d:\d\d-\d\d:\d\d$')
    for i in range(len(hour_intervals_list)):
        hour_interval = hour_intervals_list[i]
        if not pattern.match(hour_interval):
            raise ValidationError(
                'incorrect format for {} on index {}.'.format(value_title, i)
            )


class CourierItemSchema(Schema):
    courier_id = Int(validate=Range(min=0), strict=True, required=True)
    courier_type = Str(validate=OneOf([courier_type.value for courier_type in CourierType]), required=True)
    regions = List(Int(validate=Range(min=0)), strict=True, required=True)
    working_hours = List(Str(), required=True)

    @validates('working_hours')
    def validate_working_hours(self, value):
        validate_hour_intervals_with_regular_expressions(value, "working hours")
        validate_hour_intervals_list(value, "working_hours")


class CouriersPostRequestSchema(PostRequestSchema):
    data = CouriersNested(CourierItemSchema, many=True, required=True,
                          validate=Length(max=10000))  # rewrite according to courier schema

    @validates_schema
    def validate_unique_courier_id(self, data, **_):
        courier_ids_set = set()
        couriers_ids_list = list()
        for courier in data['data']:
            courier_ids_set.add(courier['courier_id'])
            couriers_ids_list.append(courier['courier_id'])
        if len(couriers_ids_list) != len(courier_ids_set):
            raise ValidationError(
                {'data': {'validation_error': [
                    {'id': i
                     } for i in [item for item in courier_ids_set if couriers_ids_list.count(item) > 1]
                ]}})


class SingleIdSchema(Schema):
    id = Int(validate=Range(min=0), strict=True, required=True)


class CouriersIdsSchema(Schema):
    couriers = Nested(SingleIdSchema, many=True, required=True,
                      validate=Length(max=10000))  # rewrite according to response schema


class CourierGetResponseSchema(CourierItemSchema):
    rating = Float(validate=Range(min=0), strict=True)
    earnings = Int(validate=Range(min=0), strict=True)


class CourierUpdateRequestSchema(Schema):
    type = Str(validate=OneOf([courier_type.value for courier_type in CourierType]))
    regions = List(Int(validate=Range(min=0)), strict=True)
    working_hours = List(Str())

    @validates('working_hours')
    def validate_working_hours(self, value):
        validate_hour_intervals_with_regular_expressions(value, "working hours")
        validate_hour_intervals_list(value, "working hours")


class OrderItemSchema(Schema):
    order_id = Int(validate=Range(min=0), strict=True, required=True)
    weight = Float(validate=Range(min=0.01, max=50), strict=True, required=True)
    region = Int(validate=Range(min=0), strict=True, required=True)
    delivery_hours = List(Str(validate=Length(min=0, max=10000)), required=True)

    @validates('delivery_hours')
    def validate_working_hours(self, value):
        validate_hour_intervals_with_regular_expressions(value, "delivery hours")
        validate_hour_intervals_list(value, "delivery hours")


class OrdersPostRequestSchema(PostRequestSchema):
    data = OrdersNested(OrderItemSchema, many=True, required=True,
                        validate=Length(max=10000))  # rewrite according to courier schema

    @validates_schema
    def validate_unique_courier_id(self, data, **_):
        ids_set = set()
        ids_list = list()
        for order in data['data']:
            ids_set.add(order['order_id'])
            ids_list.append(order['order_id'])
        if len(ids_list) != len(ids_set):
            raise ValidationError(
                {'data': {'validation_error': [
                    {'id': i
                     } for i in [item for item in ids_set if ids_list.count(item) > 1]
                ]}})


class OrdersIdsSchema(Schema):
    orders = Nested(SingleIdSchema, many=True, required=True,
                   validate=Length(max=10000))  # rewrite according to response schema


class OrdersGetResponseSchema(OrderItemSchema):
    courier_id = Int()
    assign_time = Str(strict=True)
    complete_time = Str(strict=True)


class OrdersAssignPostResponseSchema(Schema):
    orders = Nested(SingleIdSchema, many=True, required=True,
                    validate=Length(min=0, max=10000))  # rewrite according to response schema
    assign_time = Str()


class OrdersAssignPostRequestSchema(Schema):
    courier_id = Int(validate=Range(min=0), strict=True, required=True)


class OrdersCompletePostRequestSchema(Schema):
    courier_id = Int(validate=Range(min=0), strict=True, required=True)
    order_id = Int(validate=Range(min=0), strict=True, required=True)
    complete_time = Str(required=True)


class OrdersCompletePostResponseSchema(Schema):
    order_id = Int(validate=Range(min=0), strict=True, required=True)

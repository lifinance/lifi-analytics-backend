from os import RTLD_NOW, cpu_count
from re import fullmatch
from flask import request, jsonify, redirect, render_template
from flask_migrate import init
from data.models import AssetMovement, Txns, Misc, DateVolume
from apis import db, app
from data.query import fetch_txns_df, time_taken
from data.expiry_manager import get_prep_cut_off
from data.constants import chain_case_mapping
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text, func
import json

from . import blueprint

from apscheduler.schedulers.background import BackgroundScheduler

from flask_apscheduler import APScheduler

scheduler = APScheduler()


def clear_table_with_expiry(Txns, prep_cut_off):
    delete_q = Txns.__table__.delete().where(Txns.preparedTimestamp > prep_cut_off)
    db.session.execute(delete_q)
    db.session.commit()
    # except:
    #     db.session.rollback()


def init_db(df):
    rows = []
    for index, row in df.iterrows():
        new_row = Txns(
            amount=row["amount"],
            expiry=row["expiry"],
            fulfillTimestamp=row["fulfillTimestamp"],
            subgraphId=row["id"],
            preparedBlockNumber=row["preparedBlockNumber"],
            preparedTimestamp=row["preparedTimestamp"],
            receivingAssetId=row["receivingAssetId"],
            sendingAssetId=row["sendingAssetId"],
            status=row["status"],
            user=row["user"],
            chain=row["chain"],
            txn_type=row["txn_type"],
            asset_movement=row["asset_movement"],
            asset_token=row["asset_token"],
            decimals=row["decimals"],
            dollar_amount=row["dollar_amount"],
            time_prepared=row["time_prepared"],
            time_fulfilled=row["time_fulfilled"],
        )
        rows.append(new_row)

    db.session.add_all(rows)
    db.session.commit()


def add_txns(df, prep_cut_off):
    rows = []
    clear_table_with_expiry(Txns, prep_cut_off)

    for index, row in df.iterrows():
        new_row = Txns(
            amount=row["amount"],
            expiry=row["expiry"],
            fulfillTimestamp=row["fulfillTimestamp"],
            subgraphId=row["id"],
            preparedBlockNumber=row["preparedBlockNumber"],
            preparedTimestamp=row["preparedTimestamp"],
            receivingAssetId=row["receivingAssetId"],
            sendingAssetId=row["sendingAssetId"],
            status=row["status"],
            user=row["user"],
            chain=row["chain"],
            txn_type=row["txn_type"],
            asset_movement=row["asset_movement"],
            asset_token=row["asset_token"],
            decimals=row["decimals"],
            dollar_amount=row["dollar_amount"],
            time_prepared=row["time_prepared"],
            time_fulfilled=row["time_fulfilled"],
        )
        rows.append(new_row)

    db.session.add_all(rows)
    db.session.commit()

    print(df.shape[0], "rows added to Postgres")


@scheduler.task(
    "interval",
    id="job_sync",
    seconds=120,
    max_instances=1,
    start_date="2000-01-01 12:19:00",
)
def update_db():
    print("Updating database")
    with scheduler.app.app_context():
        prep_cut_off = get_prep_cut_off()

        count = db.session.query(Txns).count()
        if count == 0:
            prep_cut_off = "1232571303"
            df = fetch_txns_df(prep_cut_off)
            init_db(df)
            return
        df = fetch_txns_df(prep_cut_off)
        add_txns(df, prep_cut_off)
        update_cached_data()


# def get_last_blocs():
#     query1 = db.session.query(func.max()).filter(model.Issue.project_id == projectid)
#     sql = text('select max("preparedBlockNumber_y") from txns where chain_x="Arbitrum"')
#     result = db.engine.execute(sql)
#     rows = [row[0] for row in result]
#     count = rows[0]


def update_cached_data():
    print("updatin cached databases")
    compact_data_txns = pd.read_sql(
        sql=db.session.query(Txns).statement, con=db.session.bind
    )
    repeat_txns = compact_data_txns[compact_data_txns["txn_type"] == "repeat"].copy(
        deep=True
    )
    one_sided_txns = compact_data_txns[compact_data_txns["txn_type"] == "single"].copy(
        deep=True
    )
    repeat_txns.reset_index(drop=True, inplace=True)
    one_sided_txns.reset_index(drop=True, inplace=True)

    dem2_merge_cols = [
        "id",
        "receivingAssetId",
        "asset_token",
        "user",
        "sendingAssetId",
        "asset_movement",
    ]
    merged_txns = pd.merge(
        left=one_sided_txns,
        right=repeat_txns,
        how="outer",
        left_on=dem2_merge_cols,
        right_on=dem2_merge_cols,
    )
    print("Merged", merged_txns.shape)
    merged_txns["time_taken"] = merged_txns.apply(time_taken, axis=1)
    merged_txns["time_taken_seconds"] = merged_txns["time_taken"].apply(
        lambda x: x.seconds
    )

    # merged_txns.replace({np.NaN: None}, inplace=True)

    fulfilled_txns = merged_txns[
        (merged_txns.status_x == "Fulfilled") & (merged_txns.status_y == "Fulfilled")
    ].copy(deep=True)
    fulfilled_txns["date"] = fulfilled_txns["time_fulfilled_y"].apply(
        lambda x: x.date()
    )
    date_volume = (
        fulfilled_txns.groupby("date")
        .agg({"id": "count", "dollar_amount_x": "sum"})
        .reset_index()
        .rename(columns={"id": "txns", "dollar_amount_x": "volume"})
    )
    date_volume.to_sql("date_volume", db.engine, if_exists="replace", index_label="id")

    fulfilled_txns["time_taken_seconds"] = pd.to_numeric(
        fulfilled_txns["time_taken_seconds"], downcast="float"
    )

    asset_movement = (
        fulfilled_txns.groupby("asset_movement")
        .agg({"id": "count", "dollar_amount_x": "sum", "time_taken_seconds": "mean"})
        .reset_index()
        .rename(
            columns={
                "id": "txns",
                "dollar_amount_x": "volume",
                "time_taken_seconds": "time_taken",
            }
        )
    )
    asset_movement.to_sql(
        "asset_movement", db.engine, if_exists="replace", index_label="id"
    )

    past_day_volume = fulfilled_txns[
        fulfilled_txns["time_fulfilled_y"] >= datetime.now() - timedelta(1)
    ]["dollar_amount_x"].sum()
    misc_data = Misc.query.filter_by(data="past_day_volume").first()
    misc_data.value = str(past_day_volume)
    db.session.commit()

    past_day_count = fulfilled_txns[
        fulfilled_txns["time_fulfilled_y"] >= datetime.now() - timedelta(1)
    ]["dollar_amount_x"].count()
    misc_data = Misc.query.filter_by(data="past_day_count").first()
    misc_data.value = str(past_day_count)
    db.session.commit()

    total_unique_users = fulfilled_txns.user.nunique()
    misc_data = Misc.query.filter_by(data="total_unique_users").first()
    misc_data.value = str(total_unique_users)
    db.session.commit()

    total_volume = fulfilled_txns.dollar_amount_x.sum()
    misc_data = Misc.query.filter_by(data="total_volume").first()
    misc_data.value = str(total_volume)
    db.session.commit()

    total_txns_no = fulfilled_txns.shape[0]
    misc_data = Misc.query.filter_by(data="total_txns_no").first()
    misc_data.value = str(total_txns_no)
    db.session.commit()
    print("updated cache")


@blueprint.route("/")
def hello_world():
    rows = db.session.query(Txns).count()
    count = rows
    # sql = text("select count(*) from txns")
    # result = db.engine.execute(sql)
    # rows = [row[0] for row in result]
    # count = rows[0]
    return "Thanks for using our data :)" + str(count)


@blueprint.route("/expiry")
def get_expi():
    update_cached_data()
    return "asdfasfas"


@blueprint.route("/general_stats")
def get_general_data():
    data = [row.serialize() for row in Misc.query.all()]
    return jsonify({"data": data})


@blueprint.route("/date_volume")
def get_date_volume():
    data = [row.serialize() for row in DateVolume.query.all()]
    return jsonify({"data": data})


@blueprint.route("/asset_movement")
def get_asset_movement():
    data = [row.serialize() for row in AssetMovement.query.all()]
    return jsonify({"data": data})

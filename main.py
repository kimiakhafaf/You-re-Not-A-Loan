from flask import Flask, render_template, request, url_for, redirect
from peewee import *
import csv
import re

db = SqliteDatabase('mydb.db')


class Loans(Model):
    class Meta:
        database = db

    loan_id = TextField(unique=True, primary_key=True)
    channel = CharField()
    seller = TextField()
    interest_rate = FloatField()
    ubp = IntegerField()
    loan_term = IntegerField()
    origination_date = TextField()
    first_payment_date = TextField()
    ltv = IntegerField()
    cltv = FloatField()
    num_borrowers = IntegerField()
    dti = IntegerField()
    borrower_fico = IntegerField()
    first_time_buyer = BooleanField()
    loan_purpose = CharField()
    dwelling_type = TextField()
    unit_count = IntegerField()
    occupancy = CharField()
    state = TextField()
    zip = IntegerField()
    insurance_rate = FloatField()
    product = TextField()
    mortgage_insurance_type = IntegerField()
    relocation_indicator = BooleanField()
    period = IntegerField()
    current_ir = FloatField()
    current_upb = FloatField()
    age = IntegerField()
    mod_ind = BooleanField()
    zero_bal_cd = TextField()
    term_bins = IntegerField()
    current_status = TextField()
    origin_month = IntegerField()
    origin_year = IntegerField()


def create_database():

    db.drop_tables([Loans])
    db.create_tables([Loans])

    file_name = "Processed_loans.csv"

    with open(file_name) as fh:
        rd = csv.DictReader(fh, delimiter=',')
        for index, row in enumerate(rd):

            print(index)

            term_bin = 30 if '30' in row.get('Term_bins') else 15
            first_time_buyer = True if row.get('First_Time_Buyer') == 'Y' else False

            Loans.create(
                loan_id=row.get('Loan_ID'),
                channel=row.get('Channel'),
                seller=row.get('Seller'),
                interest_rate=row.get('Interest_Rate'),
                ubp=row.get('UPB'),
                loan_term=row.get('Loan_Term'),
                origination_date=row.get('Origination_Date'),
                first_payment_date=row.get('First_Payment_Date'),
                ltv=row.get('LTV'),
                cltv=row.get('CLTV'),
                num_borrowers=row.get('Num_Borrowers'),
                dti=row.get('DTI'),
                borrower_fico=row.get('Borrower_FICO'),
                first_time_buyer=first_time_buyer,
                loan_purpose=row.get('Loan_Purpose'),
                dwelling_type=row.get('Dwelling_Type'),
                unit_count=row.get('Unit_Count'),
                occupancy=row.get('Occupancy'),
                state=row.get('State'),
                zip=row.get('Zip'),
                insurance_rate=row.get('Insurance%'),
                product=row.get('Product'),
                mortgage_insurance_type=row.get('Mortgage_Insurance_Type'),
                relocation_indicator=row.get('Relocation_Indicator'),
                period=row.get('Period'),
                current_ir=row.get('Current_IR'),
                current_upb=row.get('Current_UPB'),
                age=row.get('Age'),
                mod_ind=row.get('Mod_Ind'),
                zero_bal_cd=row.get('Zero_Bal_Cd'),
                term_bins=term_bin,
                current_status=row.get('Current_Status'),
                origin_month=row.get('Origin_Month'),
                origin_year=row.get('Origin_Year')
            ).save()


app = Flask(__name__, template_folder="templates")


def calculate_dwelling(dwelling):

    result = db.execute_sql(f"""
            select loans.current_status, count(*)
            from loans
            where loans.dwelling_type = "{dwelling.upper()}"
            group by loans.current_status
            """).fetchall()

    total = 0
    for (_, count) in result:
        total += count

    data = []
    for (status, count) in result:
        data.append((status, count / total))

    return data


def calculate_fico(fico):

    result = db.execute_sql(f"""
            select loans.current_status, count(*)
            from loans
            where loans.borrower_fico > {fico - 10} and loans.borrower_fico < {fico + 10}
            group by loans.current_status
            """).fetchall()

    total = 0
    for (_, count) in result:
        total += count

    data = []
    for (status, count) in result:
        data.append((status, count / total))

    return data


def calculate_term(term_low, term_high, first_time_buyer):

    under = db.execute_sql(f"""
            select loans.borrower_fico, count(*)
            from loans
            where loans.interest_rate > {term_low} and 
                  loans.interest_rate < {term_high} and
                  loans.first_time_buyer = {0 if first_time_buyer else 1} and 
                  loans.current_status = "Underperforming"
            group by loans.borrower_fico
            order by loans.borrower_fico
    """)

    prepaid = db.execute_sql(f"""
                select loans.borrower_fico, count(*)
                from loans
                where loans.interest_rate > {term_low} and 
                      loans.interest_rate < {term_high} and
                      loans.first_time_buyer = {0 if first_time_buyer else 1} and 
                      loans.current_status = "Prepaid"
                group by loans.borrower_fico
                order by loans.borrower_fico
    """)

    current = db.execute_sql(f"""
                select loans.borrower_fico, count(*)
                from loans
                where loans.interest_rate > {term_low} and 
                      loans.interest_rate < {term_high} and
                      loans.first_time_buyer = {0 if first_time_buyer else 1} and 
                      loans.current_status = "Current"
                group by loans.borrower_fico
                order by loans.borrower_fico
    """)

    return under, prepaid, current


def calculate_state(state):

    try:
        result = db.execute_sql(f"""
                select loans.borrower_fico, count(*)
                from loans
                where loans.current_status = "Underperforming" and loans.state = "{state.upper()}"
                group by loans.borrower_fico
                order by loans.borrower_fico
            """).fetchall()
        return result
    except Exception as e:
        print(e)
        return []


def default_pie():

    result = db.execute_sql(f"""
            select loans.current_status, count(*)
            from loans
            group by loans.current_status
        """).fetchall()

    total = 0
    for (_, count) in result:
        total += count

    data = []
    for (status, count) in result:
        data.append((status, count / total))

    return data


def default_column():

    result = db.execute_sql("""
            select loans.borrower_fico, count(*)
            from loans
            where loans.current_status = "Underperforming"
            group by loans.borrower_fico
            order by loans.borrower_fico
        """).fetchall()

    return result


@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'POST':
        print(request.form)

        dwelling = request.form.get('dwelling')
        dwelling_result = calculate_dwelling(dwelling)
        first_time = bool(request.form.get('first_time', False))
        state = request.form.get('state')
        fico = int(request.form.get('fico'))
        term = int(request.form.get('term'))
        interest = request.form.getlist('interest')
        borrowers = int(request.form.get('borrowers', 1))

        under, prepaid, current = calculate_term(interest[0], interest[1], first_time)

        return render_template("custom_form.html",
                               dwelling=calculate_dwelling(dwelling),
                               dwelling_value=dwelling,
                               fico=calculate_fico(fico),
                               fico_value=fico,
                               state=calculate_state(state),
                               state_value=state,
                               under=under, prepaid=prepaid, current=current)

    return render_template('form.html',
                           default_pie=default_pie(),
                           default_column=default_column())


@app.route('/column', methods=['GET'])
def column():

    result = db.execute_sql("""
        select loans.borrower_fico, count(*)
        from loans
        where loans.current_status = "Underperforming"
        group by loans.borrower_fico
        order by loans.borrower_fico
    """).fetchall()

    print(result)
    return render_template("column.html", result=result)


@app.route('/pie', methods=['GET'])
def overall_pie():

    result = db.execute_sql(f"""
        select loans.current_status, count(*)
        from loans
        group by loans.current_status
    """).fetchall()

    total = 0
    for (_, count) in result:
        total += count

    data = []
    for (status, count) in result:
        data.append((status, count / total))

    return render_template("pie.html", data=data)


@app.route('/pie/<state>', methods=['GET'])
def pie(state):

    result = db.execute_sql(f"""
        select loans.current_status, count(*)
        from loans
        where loans.state = '{state.upper()}'
        group by loans.current_status
    """).fetchall()

    total = 0
    for (_, count) in result:
        total += count

    data = []
    for (status, count) in result:
        data.append((status, count / total))

    return render_template("pie.html", data=data)


def main():
    app.run(host="0.0.0.0", port=8081, debug=True)


if __name__ == '__main__':
    main()


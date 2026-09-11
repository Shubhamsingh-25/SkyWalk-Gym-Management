import streamlit as st
from database import supabase
from datetime import date
from dateutil.relativedelta import relativedelta
import qrcode
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


st.set_page_config(
    page_title="Sky Walk Gym",
    page_icon="🏋️",
    layout="wide"
)


# =========================================================
# SESSION
# =========================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "gym" not in st.session_state:
    st.session_state.gym = None


# =========================================================
# AUTH
# =========================================================

def login_screen():

    st.title("🏋️ Sky Walk Gym Management System")

    login, signup = st.tabs(["🔐 Login", "📝 Create Account"])

    with login:

        email = st.text_input("Email", key="login_email")
        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login", type="primary", use_container_width=True):

            try:
                result = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

                st.session_state.user = result.user
                st.rerun()

            except Exception as e:
                st.error("Login failed")
                st.code(str(e))

    with signup:

        email = st.text_input("Email", key="signup_email")
        password = st.text_input(
            "Password",
            type="password",
            key="signup_password"
        )

        if st.button("Create Account", use_container_width=True):

            try:

                result = supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })

                if result.user:
                    st.success(
                        "Account created. Please confirm your email."
                    )

            except Exception as e:
                st.error(str(e))


# =========================================================
# LOAD GYM
# =========================================================

def load_gym():

    result = (
        supabase
        .table("gyms")
        .select("*")
        .eq(
            "owner_user_id",
            str(st.session_state.user.id)
        )
        .limit(1)
        .execute()
    )

    return result.data[0] if result.data else None


# =========================================================
# GYM SETUP
# =========================================================

def gym_setup():

    st.title("🏋️ Welcome to Sky Walk Gym")
    st.subheader("Gym Setup")

    name = st.text_input("Gym Name", value="Sky Walk Gym")
    owner = st.text_input("Owner Name")
    phone = st.text_input("Phone Number")
    email = st.text_input("Gym Email")
    address = st.text_area("Gym Address")

    if st.button(
        "Create Gym",
        type="primary",
        use_container_width=True
    ):

        try:

            result = (
                supabase
                .table("gyms")
                .insert({
                    "name": name,
                    "owner_user_id": str(
                        st.session_state.user.id
                    ),
                    "owner_name": owner,
                    "phone": phone,
                    "email": email,
                    "address": address
                })
                .execute()
            )

            st.session_state.gym = result.data[0]

            st.success("Gym created successfully 🎉")

            st.rerun()

        except Exception as e:

            st.error("Could not create gym")
            st.code(str(e))


# =========================================================
# HELPERS
# =========================================================

def gym_id():
    return st.session_state.gym["id"]


def get_members():

    result = (
        supabase
        .table("v_member_status")
        .select("*")
        .eq("gym_id", gym_id())
        .execute()
    )

    return result.data


def get_plans():

    result = (
        supabase
        .table("membership_plans")
        .select("*")
        .eq("gym_id", gym_id())
        .eq("is_active", True)
        .order("price")
        .execute()
    )

    return result.data


# =========================================================
# DASHBOARD
# =========================================================

def dashboard():

    members = get_members()

    active = [
        x for x in members
        if x.get("membership_status") == "active"
    ]

    expiring = [
        x for x in members
        if x.get("membership_status") == "expiring_soon"
    ]

    today = date.today().isoformat()

    attendance = (
        supabase
        .table("attendance")
        .select("id")
        .eq("gym_id", gym_id())
        .eq("attendance_date", today)
        .execute()
    )

    st.title(f"🏋️ {st.session_state.gym['name']}")

    st.caption(
        f"Welcome, "
        f"{st.session_state.gym.get('owner_name') or 'Owner'}"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Members", len(members))
    c2.metric("Active Members", len(active))
    c3.metric("Expiring Soon", len(expiring))
    c4.metric("Today's Attendance", len(attendance.data))

    st.divider()

    # =====================================================
    # MEMBERSHIP EXPIRY ALERTS
    # =====================================================

    expired = [
        x for x in members
        if x.get("membership_status") == "expired"
    ]

    st.subheader("🔔 Membership Alerts")

    if expiring:
        st.warning(
            f"⚠️ {len(expiring)} member(s) have membership expiring soon."
        )

        st.dataframe(
            [
                {
                    "Member ID": x["member_code"],
                    "Name": x["full_name"],
                    "Plan": x.get("plan_name_snapshot") or "-",
                    "Expiry Date": x.get("end_date") or "-",
                    "Status": "Expiring Soon"
                }
                for x in expiring
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ No memberships are expiring soon.")

    if expired:
        st.error(
            f"🚨 {len(expired)} member(s) have expired membership."
        )

        st.dataframe(
            [
                {
                    "Member ID": x["member_code"],
                    "Name": x["full_name"],
                    "Plan": x.get("plan_name_snapshot") or "-",
                    "Expiry Date": x.get("end_date") or "-",
                    "Status": "Expired"
                }
                for x in expired
            ],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader("📋 Recent Members")

    if members:

        st.dataframe(
            [
                {
                    "Member ID": x["member_code"],
                    "Name": x["full_name"],
                    "Phone": x["phone"],
                    "Plan": x.get("plan_name_snapshot") or "-",
                    "Start": x.get("start_date") or "-",
                    "Expiry": x.get("end_date") or "-",
                    "Status": x.get("membership_status")
                }
                for x in members[:10]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No members yet. Add your first member from Members."
        )


# =========================================================
# MEMBERS
# =========================================================

def members_page():

    st.title("👥 Members")

    tab1, tab2 = st.tabs([
        "➕ Add Member",
        "📋 All Members"
    ])

    with tab1:

        with st.form("member_form"):

            col1, col2 = st.columns(2)

            with col1:

                member_code = st.text_input(
                    "Member ID *",
                    placeholder="SW001"
                )

                full_name = st.text_input(
                    "Full Name *"
                )

                phone = st.text_input(
                    "Phone Number *"
                )

                email = st.text_input(
                    "Email"
                )

            with col2:

                gender = st.selectbox(
                    "Gender",
                    ["Male", "Female", "Other"]
                )

                dob = st.date_input(
                    "Date of Birth",
                    value=None,
                    min_value=date.today() - relativedelta(years=70),
                    max_value=date.today()
                )

                join_date = st.date_input(
                    "Join Date",
                    value=date.today()
                )

            emergency_name = st.text_input(
                "Emergency Contact Name"
            )

            emergency_phone = st.text_input(
                "Emergency Contact Phone"
            )

            notes = st.text_area("Notes")

            submitted = st.form_submit_button(
                "Add Member",
                type="primary",
                use_container_width=True
            )

            if submitted:

                if not member_code or not full_name or not phone:

                    st.warning(
                        "Member ID, Name and Phone are required."
                    )

                else:

                    try:

                        data = {
                            "gym_id": gym_id(),
                            "member_code": member_code,
                            "full_name": full_name,
                            "phone": phone,
                            "email": email or None,
                            "gender": gender,
                            "date_of_birth": (
                                dob.isoformat()
                                if dob else None
                            ),
                            "join_date": join_date.isoformat(),
                            "emergency_contact_name":
                                emergency_name or None,
                            "emergency_contact_phone":
                                emergency_phone or None,
                            "notes": notes or None
                        }

                        supabase.table(
                            "members"
                        ).insert(data).execute()

                        st.success(
                            f"{full_name} added successfully! 🎉"
                        )

                    except Exception as e:

                        st.error("Could not add member.")
                        st.code(str(e))

    with tab2:

        members = get_members()

        if members:

            search = st.text_input(
                "🔎 Search name / phone / member ID"
            )

            if search:

                search = search.lower()

                members = [
                    x for x in members
                    if search in x["full_name"].lower()
                    or search in x["phone"].lower()
                    or search in x["member_code"].lower()
                ]

            st.dataframe(
                [
                    {
                        "Member ID": x["member_code"],
                        "Name": x["full_name"],
                        "Phone": x["phone"],
                        "Plan": x.get("plan_name_snapshot") or "-",
                        "Expiry": x.get("end_date") or "-",
                        "Status": x.get("membership_status")
                    }
                    for x in members
                ],
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info("No members found.")


# =========================================================
# PLANS
# =========================================================

def plans_page():

    st.title("💳 Membership Plans")

    with st.form("plan_form"):

        plan_options = {
            "Monthly": 1,
            "Quarterly": 3,
            "Half Yearly": 6,
            "Yearly": 12
        }

        name = st.selectbox(
            "Plan Name",
            list(plan_options.keys())
        )

        duration = plan_options[name]

        st.info(
            f"Membership Duration: **{duration} Month(s)**"
        )

        price = st.number_input(
            "Price (₹)",
            min_value=0.0,
            value=1000.0,
            step=100.0
        )

        description = st.text_input(
            "Description",
            placeholder="Enter plan details"
        )

        if st.form_submit_button(
            "Create Plan",
            type="primary",
            use_container_width=True
        ):

            try:

                supabase.table(
                    "membership_plans"
                ).insert({
                    "gym_id": gym_id(),
                    "name": name,
                    "duration_months": int(duration),
                    "price": price,
                    "description": description or None
                }).execute()

                st.success(
                    f"{name} plan created successfully!"
                )

            except Exception as e:

                st.error("Could not create plan.")
                st.code(str(e))

    st.divider()

    plans = get_plans()

    if plans:

        st.dataframe(
            [
                {
                    "Plan": p["name"],
                    "Duration": f"{p['duration_months']} Month(s)",
                    "Price": f"₹{p['price']:,.2f}",
                    "Description": p.get("description") or "-"
                }
                for p in plans
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No membership plans created yet.")


# =========================================================
# PAYMENT RECEIPT PDF
# =========================================================

def generate_receipt_pdf(
    receipt_no,
    member,
    plan,
    purchased_on,
    start_date,
    end_date,
    amount,
    discount,
    payment_method,
    transaction_ref
):
    """Generate a professional PDF payment receipt."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=22,
        leading=26,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=18
    )

    story = []

    story.append(Paragraph("SKY WALK GYM", title_style))
    story.append(Paragraph("Membership Payment Receipt", subtitle_style))

    receipt_info = [
        ["Receipt No.", str(receipt_no), "Payment Date", purchased_on.strftime("%d-%m-%Y")],
        ["Member ID", str(member["member_code"]), "Member Name", str(member["full_name"])],
    ]

    info_table = Table(receipt_info, colWidths=[85, 150, 85, 150])
    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("BACKGROUND", (2, 0), (2, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 18))

    membership_data = [
        ["Membership Details", "Value"],
        ["Plan", str(plan["name"])],
        ["Duration", f'{plan["duration_months"]} Month(s)'],
        ["Membership Start", start_date.strftime("%d-%m-%Y")],
        ["Membership End", end_date.strftime("%d-%m-%Y")],
        ["Plan Price", f'Rs. {float(plan["price"]):,.2f}'],
        ["Discount", f"Rs. {float(discount):,.2f}"],
        ["Amount Paid", f"Rs. {float(amount):,.2f}"],
        ["Payment Method", str(payment_method).replace("_", " ").title()],
        ["Transaction Reference", str(transaction_ref or "-")],
    ]

    membership_table = Table(membership_data, colWidths=[220, 250])
    membership_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(membership_table)
    story.append(Spacer(1, 24))

    story.append(Paragraph(
        "Thank you for choosing Sky Walk Gym. Keep this receipt for your records.",
        styles["Normal"]
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# MEMBERSHIP
# =========================================================

def membership_page():

    st.title("🎫 Create Membership")

    members = get_members()
    plans = get_plans()

    if not members:

        st.warning("Please add a member first.")
        return

    if not plans:

        st.warning("Please create a membership plan first.")
        return

    member_map = {
        f"{m['member_code']} - {m['full_name']}":
        m for m in members
    }

    plan_map = {
        f"{p['name']} - ₹{p['price']}":
        p for p in plans
    }

    selected_member = st.selectbox(
        "Member",
        list(member_map.keys())
    )

    selected_plan = st.selectbox(
        "Plan",
        list(plan_map.keys())
    )

    member = member_map[selected_member]
    plan = plan_map[selected_plan]

    col1, col2 = st.columns(2)

    with col1:

        purchased_on = st.date_input(
            "Payment / Purchase Date",
            value=date.today()
        )

    with col2:

        start_date = st.date_input(
            "Membership Start Date",
            value=date.today()
        )

    discount = st.number_input(
        "Discount (₹)",
        min_value=0.0,
        max_value=float(plan["price"]),
        value=0.0,
        step=50.0
    )

    amount = float(plan["price"]) - float(discount)

    end_date = (
        start_date
        + relativedelta(months=int(plan["duration_months"]))
        - relativedelta(days=1)
    )

    st.info(
        f"Membership End Date: **{end_date}**"
    )

    st.metric(
        "Amount Payable",
        f"₹{amount:,.2f}"
    )

    payment_method = st.selectbox(
        "Payment Method",
        ["cash", "upi", "card", "bank_transfer", "other"]
    )

    transaction_ref = st.text_input(
        "Transaction Reference"
    )

    if st.button(
        "Create Membership & Payment",
        type="primary",
        use_container_width=True
    ):

        try:

            membership_result = (
                supabase
                .table("memberships")
                .insert({
                    "gym_id": gym_id(),
                    "member_id": member["member_id"],
                    "plan_id": plan["id"],
                    "purchased_on": purchased_on.isoformat(),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "plan_name_snapshot": plan["name"],
                    "amount": amount,
                    "discount": discount,
                    "status": (
                        "active"
                        if start_date <= date.today()
                        else "scheduled"
                    )
                })
                .execute()
            )

            membership_id = membership_result.data[0]["id"]

            receipt_no = (
                f"SW-{purchased_on.strftime('%Y%m%d')}-"
                f"{member['member_code']}-"
                f"{str(membership_id).split('-')[0].upper()}"
            )

            supabase.table(
                "payments"
            ).insert({
                "gym_id": gym_id(),
                "member_id": member["member_id"],
                "membership_id": membership_id,
                "receipt_no": receipt_no,
                "payment_date": purchased_on.isoformat(),
                "amount": amount,
                "payment_method": payment_method,
                "transaction_ref":
                    transaction_ref or None,
                "created_by":
                    str(st.session_state.user.id)
            }).execute()

            st.success(
                f"Membership created! Receipt: {receipt_no}"
            )

            receipt_pdf = generate_receipt_pdf(
                receipt_no=receipt_no,
                member=member,
                plan=plan,
                purchased_on=purchased_on,
                start_date=start_date,
                end_date=end_date,
                amount=amount,
                discount=discount,
                payment_method=payment_method,
                transaction_ref=transaction_ref
            )

            st.download_button(
                label="📄 Download Payment Receipt (PDF)",
                data=receipt_pdf,
                file_name=f"{receipt_no}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        except Exception as e:

            st.error("Could not create membership/payment.")
            st.code(str(e))


# =========================================================
# ATTENDANCE
# =========================================================

def mark_attendance(member_id, source="manual"):
    supabase.table("attendance").insert({
        "gym_id": gym_id(),
        "member_id": member_id,
        "attendance_date": date.today().isoformat(),
        "source": source,
        "created_by": str(st.session_state.user.id)
    }).execute()


def get_public_app_url():
    """Public URL used by the General Gym QR code."""
    try:
        url = st.secrets.get("PUBLIC_APP_URL", "")
    except Exception:
        url = ""
    return str(url).strip().rstrip("/")


def generate_general_qr():
    """Generate ONE QR for all members to self-check-in."""
    public_url = get_public_app_url()

    if not public_url:
        st.warning(
            "PUBLIC_APP_URL is not configured yet. After deployment, "
            "add your Streamlit public URL to .streamlit/secrets.toml."
        )
        st.code('PUBLIC_APP_URL = "https://your-app.streamlit.app"')
        return

    checkin_url = f"{public_url}?checkin=1"
    qr_image = qrcode.make(checkin_url)
    qr_buffer = io.BytesIO()
    qr_image.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    st.image(qr_buffer.getvalue(), width=280)
    st.success("This is the General Gym QR. Members scan this from their own phone.")
    st.caption("Keep this QR at the gym entrance/reception.")

    with st.expander("Show check-in URL"):
        st.code(checkin_url)


def attendance_page():
    st.title("📅 Attendance")

    tab1, tab2 = st.tabs([
        "📱 General Gym QR",
        "✋ Manual Attendance"
    ])

    with tab1:
        st.subheader("📱 Member Self Check-in")
        st.write(
            "Generate one General Gym QR. Members scan it using their own phone, "
            "verify their Member ID and registered phone number, and attendance "
            "is marked automatically."
        )
        generate_general_qr()

    with tab2:
        st.subheader("Manual Attendance")
        members = get_members()
        if not members:
            st.info("Add members first.")
        else:
            member_map = {f"{m['member_code']} - {m['full_name']}": m for m in members}
            selected = st.selectbox(
                "Select Member",
                list(member_map.keys()),
                key="manual_attendance_member"
            )
            member = member_map[selected]
            if st.button(
                "✅ Mark Today's Attendance",
                type="primary",
                use_container_width=True
            ):
                try:
                    mark_attendance(member["member_id"], "manual")
                    st.success(
                        f"Attendance marked for {member['full_name']}!"
                    )
                except Exception as e:
                    st.error(
                        "Attendance already marked today or an error occurred."
                    )
                    st.code(str(e))

    st.divider()
    st.subheader("Today's Attendance")
    members = get_members()
    result = (
        supabase
        .table("attendance")
        .select("*")
        .eq("gym_id", gym_id())
        .eq("attendance_date", date.today().isoformat())
        .order("check_in_at", desc=True)
        .execute()
    )

    if result.data:
        rows = []
        for a in result.data:
            m = next(
                (x for x in members if x["member_id"] == a["member_id"]),
                None
            )
            rows.append({
                "Member ID": m["member_code"] if m else "-",
                "Name": m["full_name"] if m else "-",
                "Date": a.get("attendance_date"),
                "Check In": a.get("check_in_at"),
                "Source": a.get("source", "manual")
            })
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No attendance today.")


# =========================================================
# PUBLIC MEMBER SELF CHECK-IN
# =========================================================

def public_self_checkin():
    """Public page opened when a member scans the General Gym QR."""
    st.title("🏋️ Sky Walk Gym")
    st.subheader("📱 Member Self Check-in")
    st.write("Scan complete. Please verify your details below.")

    member_code = st.text_input(
        "Member ID",
        placeholder="Example: SW001",
        max_chars=30
    )
    phone = st.text_input(
        "Registered Phone Number",
        placeholder="Enter the phone number registered with the gym",
        max_chars=20
    )

    st.caption("Your Member ID and phone number must match the gym records.")

    if st.button(
        "✅ Mark My Attendance",
        type="primary",
        use_container_width=True
    ):
        if not member_code.strip() or not phone.strip():
            st.warning("Please enter both Member ID and phone number.")
            return

        try:
            result = supabase.rpc(
                "member_self_checkin",
                {
                    "p_member_code": member_code.strip(),
                    "p_phone": phone.strip()
                }
            ).execute()

            data = result.data
            if isinstance(data, list) and data:
                data = data[0]

            if isinstance(data, dict) and data.get("success"):
                st.success("🎉 Attendance Marked Successfully!")
                st.markdown(f"### Welcome, {data.get('member_name', 'Member')} 👋")
                st.info(
                    f"Member ID: {data.get('member_code', member_code.upper())}\n\n"
                    f"Check-in time: {data.get('check_in_at', '-') }"
                )
            elif isinstance(data, dict):
                st.error(data.get("message", "Unable to mark attendance."))
            else:
                st.error("Unable to verify member details.")

        except Exception as e:
            st.error("Could not mark attendance. Please contact gym staff.")
            st.code(str(e))


# =========================================================
# PAYMENTS
# =========================================================

def payments_page():

    st.title("💰 Payments")

    result = (
        supabase
        .table("payments")
        .select("*")
        .eq("gym_id", gym_id())
        .order("payment_date", desc=True)
        .execute()
    )

    payments = result.data

    total = sum(
        float(x["amount"])
        for x in payments
        if x["payment_status"] == "paid"
    )

    st.metric(
        "Total Paid",
        f"₹{total:,.2f}"
    )

    if payments:

        st.dataframe(
            [
                {
                    "Receipt": x["receipt_no"],
                    "Date": x["payment_date"],
                    "Amount": f"₹{float(x['amount']):,.2f}",
                    "Method": x["payment_method"],
                    "Status": x["payment_status"]
                }
                for x in payments
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No payments yet.")


# =========================================================
# PUBLIC ROUTE
# =========================================================
# General Gym QR opens the app with ?checkin=1.
# This route must be handled before owner/staff authentication.

if st.query_params.get("checkin") == "1":
    public_self_checkin()
    st.stop()


# =========================================================
# MAIN
# =========================================================

if st.session_state.user is None:

    login_screen()

else:

    if st.session_state.gym is None:
        st.session_state.gym = load_gym()

    if st.session_state.gym is None:

        gym_setup()

    else:

        with st.sidebar:

            st.title("🏋️ Sky Walk Gym")

            page = st.radio(
                "Navigation",
                [
                    "📊 Dashboard",
                    "👥 Members",
                    "💳 Membership Plans",
                    "🎫 Membership",
                    "📅 Attendance",
                    "💰 Payments"
                ]
            )

            st.divider()

            st.caption(
                st.session_state.user.email
            )

            if st.button(
                "🚪 Logout",
                use_container_width=True
            ):

                supabase.auth.sign_out()

                st.session_state.user = None
                st.session_state.gym = None

                st.rerun()

        if page == "📊 Dashboard":
            dashboard()

        elif page == "👥 Members":
            members_page()

        elif page == "💳 Membership Plans":
            plans_page()

        elif page == "🎫 Membership":
            membership_page()

        elif page == "📅 Attendance":
            attendance_page()

        elif page == "💰 Payments":
            payments_page()
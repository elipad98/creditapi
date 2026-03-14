import streamlit as st
import requests
from datetime import datetime

API = "http://localhost:8000"

st.set_page_config(page_title="CreditOS", layout="wide")
st.title("Sistema de Crédito")

def get(path):
    try:
        r = requests.get(f"{API}{path}", timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def post(path, json=None, files=None, data=None):
    try:
        r = requests.post(f"{API}{path}", json=json, files=files,
                          data=data, timeout=120)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.HTTPError as e:
        try:    msg = e.response.json().get("detail", str(e))
        except: msg = str(e)
        return None, msg
    except Exception as e:
        return None, str(e)

def estado(s):
    return {"approved":"Aprobada","rejected":"Rechazada",
            "pending":"Pendiente","under_review":"En revisión",
            "documents_required":"Docs requeridos"}.get(s, s)


pagina = st.sidebar.radio("Menú", [
    "Dashboard",
    "Solicitudes",
    "Nueva Solicitud",
    "Diagnóstico IA",
])
if pagina == "Dashboard":
    st.header("Dashboard")

    data, err = get("/dashboard")
    if err:
        st.error(f"No se puede conectar con la API: {err}")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total",       data["total_all_time"])
    col2.metric("Aprobadas",   data["approved_count"])
    col3.metric("Rechazadas",  data["rejected_count"])
    col4.metric("Pendientes",  data["pending_count"])

    if data.get("avg_credit_score"):
        st.write(f"**Score promedio:** {int(data['avg_credit_score'])} pts")
    if data.get("top_rejection_reason"):
        st.write(f"**Principal motivo de rechazo:** {data['top_rejection_reason']}")

    st.subheader("Últimas solicitudes")
    apps, _ = get("/applications?limit=10")
    if apps:
        for a in apps:
            st.write(f"#{a['id']} — {a['full_name']} | {estado(a['status'])} | ${a['requested_amount']:,.0f} MXN")
    else:
        st.info("No hay solicitudes.")

elif pagina == "Solicitudes":
    st.header("Solicitudes")

    app_id = st.number_input("ID de solicitud", min_value=1, step=1, value=1)
    if st.button("Buscar"):
        app, err = get(f"/applications/{app_id}")
        if err:
            st.error(err)
        else:
            st.subheader(f"#{app['id']} — {app['full_name']}")
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Estado:** {estado(app['status'])}")
            col2.write(f"**Score:** {app.get('credit_score') or '—'}")
            col3.write(f"**Monto:** ${app['requested_amount']:,.0f} MXN")

            if app.get("decision_explanation"):
                if app["decision"] == "approved":
                    st.success(app["decision_explanation"])
                else:
                    st.error(app["decision_explanation"])

          
            st.subheader("Documentos")
            docs = app.get("documents", [])
            if docs:
                for d in docs:
                    st.write(f"**{d['filename']}** ({d['document_type']})")
                    if d.get("extracted_name"):
                        st.write(f"  Nombre extraído: {d['extracted_name']}")
                    if d.get("extracted_address"):
                        st.write(f"  Dirección extraída: {d['extracted_address']}")
                    if d.get("address_match_score") is not None:
                        st.write(f"  Coincidencia: {d['address_match_score']:.0%}")
            else:
                st.info("Sin documentos.")

            st.subheader("Subir comprobante")
            doc_type = st.selectbox("Tipo", ["proof_of_address", "id", "income_proof"])
            archivo  = st.file_uploader("Archivo (PDF, PNG, JPG)", type=["pdf","png","jpg","jpeg","webp"])
            if archivo and st.button("Subir"):
                result, err = post(
                    f"/applications/{app_id}/documents",
                    files={"file": (archivo.name, archivo.getvalue(), archivo.type)},
                    data={"document_type": doc_type},
                )
                if err:   st.error(err)
                else:     st.success("Documento subido. Espera ~10s y vuelve a buscar para ver el resultado.")

            
            if st.button("Re-evaluar solicitud"):
                result, err = post(f"/applications/{app_id}/evaluate")
                if err:   st.error(err)
                else:     st.success(f"Re-evaluada → {estado(result['status'])}")
            

    
    st.subheader("Todas las solicitudes")
    apps, err = get("/applications?limit=20")
    if err:
        st.error(err)
    elif apps:
        import pandas as pd
        df = pd.DataFrame([{
            "ID": a["id"], "Nombre": a["full_name"],
            "Estado": estado(a["status"]),
            "Score": a.get("credit_score") or "—",
            "Monto": f"${a['requested_amount']:,.0f}",
            "Fecha": a["created_at"][:10],
        } for a in apps])
        st.dataframe(df, use_container_width=True, hide_index=True)

elif pagina == "Nueva Solicitud":
    st.header("Nueva Solicitud")

    with st.form("solicitud_form"):
        st.subheader("Datos personales")
        nombre = st.text_input("Nombre completo *")
        email = st.text_input("Email *")
        
        c1, c2 = st.columns(2)
        rfc = c1.text_input("RFC * (12-13 chars)")
        curp = c2.text_input("CURP * (18 chars)")
        
        telefono = st.text_input("Teléfono *")
        fecha_nac = st.date_input("Fecha de nacimiento *", value=datetime(1990,1,1))
        genero = st.selectbox("Género *", ["female","male","other"],
                            format_func=lambda x: {"female":"Femenino","male":"Masculino","other":"Otro"}[x])

        st.subheader("Domicilio")
        calle = st.text_input("Calle *")
        c1, c2 = st.columns(2)
        num_ext = c1.text_input("Núm. exterior *")
        num_int = c2.text_input("Núm. interior")
        
        colonia = st.text_input("Colonia *")
        ciudad = st.text_input("Ciudad *")
        estado_dir = st.text_input("Estado *")
        cp = st.text_input("C.P. *", max_chars=5)

        st.subheader("Datos financieros")
        ingreso = st.number_input("Ingreso mensual (MXN) *", min_value=0.0, step=500.0, value=10000.0)
        gastos = st.number_input("Gastos mensuales (MXN)", min_value=0.0, step=500.0, value=3000.0)
        deudas = st.number_input("Deudas actuales (MXN)", min_value=0.0, step=500.0)
        antiguedad = st.number_input("Antigüedad bancaria (meses)", min_value=0, step=1, value=12)
        empleador = st.text_input("Empleador")

        st.subheader("Solicitud")
        c1, c2 = st.columns(2)
        monto = c1.number_input("Monto solicitado (MXN) *", min_value=1000.0, step=1000.0, value=30000.0)
        plazo = c2.selectbox("Plazo (meses)", [6,12,18,24,36])

        enviar = st.form_submit_button("Crear solicitud")
    if enviar:
        
            st.success("Solicitud creada exitosamente")

    if enviar:
        errores = []
        if not nombre.strip():            errores.append("Nombre requerido")
        if not email.strip():             errores.append("Email requerido")
        if len(rfc.strip()) not in(12,13):errores.append("RFC: 12 o 13 caracteres")
        if len(curp.strip()) != 18:       errores.append("CURP: 18 caracteres")
        if not calle.strip():             errores.append("Calle requerida")
        if not colonia.strip():           errores.append("Colonia requerida")
        if not ciudad.strip():            errores.append("Ciudad requerida")
        if not cp.strip():                errores.append("C.P. requerido")
        if ingreso <= 0:                  errores.append("Ingreso debe ser mayor a 0")

        if errores:
            for e in errores: st.error(e)
        else:
            payload = {
                "full_name": nombre.strip(), "rfc": rfc.strip().upper(),
                "curp": curp.strip().upper(), "email": email.strip(),
                "phone": telefono.strip(),
                "birth_date": fecha_nac.strftime("%Y-%m-%dT00:00:00"),
                "gender": genero, "nationality": "Mexicana",
                "street": calle.strip(), "exterior_number": num_ext.strip(),
                "interior_number": num_int.strip() or None,
                "neighborhood": colonia.strip(), "city": ciudad.strip(),
                "state": estado_dir.strip(), "zip_code": cp.strip(),
                "monthly_income": ingreso, "monthly_expenses": gastos,
                "banking_seniority_months": antiguedad, "current_debts": deudas,
                "employment_type": "employed",
                "employer_name": empleador.strip() or None,
                "requested_amount": monto, "requested_term_months": plazo,
            }
            with st.spinner("Creando..."):
                result, err = post("/applications", json=payload)
            if err:
                st.error(err)
            else:
                st.success(f"Solicitud #{result['id']} creada para {result['full_name']}")
                st.info("Ve a Solicitudes y sube el comprobante de domicilio.")

elif pagina == "Diagnóstico IA":
    st.header("Diagnóstico IA")

    st.subheader("Conexión con Ollama")
    if st.button("Probar conexión"):
        with st.spinner("Probando..."):
            data, err = get("/ai/test")
        if err:
            st.error(err)
        elif data.get("status") == "ok":
            st.success(f"Ollama conectado — modelo: {data['model']} — {data['elapsed_seconds']}s")
        else:
            st.error(data.get("message"))

    st.subheader("Modelos disponibles")
    if st.button("Listar modelos"):
        data, err = get("/ai/models")
        if err:   st.error(err)
        elif data.get("models"):
            for m in data["models"]: st.write(f"• `{m}`")
        else:
            st.warning("Sin modelos. Ejecuta: ollama pull llama3.1:8b")


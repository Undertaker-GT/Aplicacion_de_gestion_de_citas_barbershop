from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import smtplib
from flask import jsonify
from datetime import datetime, date, time, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
import uuid  # para nombres únicos de archivos
from werkzeug.utils import secure_filename
from io import StringIO
import csv


# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Configuración del email
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def send_confirmation_email(email, token):
    try:
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg['Subject'] = "Confirma tu cuenta en BLANK concept"
        
        # Cuerpo del mensaje
        confirmation_url = f"http://localhost:5000/confirmar/{token}"
        body = f"""
        <h2>Gracias por registrarte en BLANK concept!</h2>
        <p>Por favor confirma tu cuenta haciendo clic en el siguiente enlace:</p>
        <a href="{confirmation_url}">Confirmar cuenta</a>
        <p>Si no has solicitado este registro, por favor ignora este mensaje.</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Enviar el email
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error al enviar email: {e}")
        return False

# muestra la página de bienvenida
@app.route('/')
def home():
    # Obtener servicios para mostrar en la página principal
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM servicios LIMIT 6")
    servicios = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('index.html', servicios=servicios)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM USUARIO WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['contraseña'], password):
            if user['confirmado'] == 1:
                session['user_id'] = user['usuario_id']
                session['user_email'] = user['email']
                session['user_role'] = user['rol']
                session['user_name'] = user['nombre']
                
                # Redirigir según el rol
                if user['rol'] == 1:
                    return redirect(url_for('admin_dashboard'))
                elif user['rol'] == 2:
                    return redirect(url_for('barber_dashboard'))
                else:
                    return redirect(url_for('client_dashboard'))
            else:
                flash('Por favor confirma tu cuenta antes de iniciar sesión. Revisa tu correo electrónico.', 'warning')
                return redirect(url_for('login'))
        else:
            flash('Correo electrónico o contraseña incorrectos', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        segundo_nombre = request.form.get('segundo_nombre')
        apellido = request.form.get('apellido')
        segundo_apellido = request.form.get('segundo_apellido')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')
        
        # Validaciones básicas
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('registro'))
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('registro'))
        
        # Verificar si el email ya existe
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT email FROM USUARIO WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            flash('Este correo electrónico ya está registrado', 'danger')
            return redirect(url_for('registro'))
        
        # Hash de la contraseña
        hashed_password = generate_password_hash(password)
        
        # Generar token de confirmación
        token = secrets.token_hex(8)
        
        # Insertar nuevo usuario
        try:
            cursor.execute(
                "INSERT INTO USUARIO (nombre, segundo_nombre, apellido, segundo_apellido, email, telefono, contraseña, token) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (nombre, segundo_nombre, apellido, segundo_apellido, email, telefono, hashed_password, token)
            )
            conn.commit()
            
            # Enviar email de confirmación
            if send_confirmation_email(email, token):
                flash('Registro exitoso! Por favor revisa tu correo para confirmar tu cuenta.', 'success')
            else:
                flash('Registro exitoso, pero no pudimos enviar el email de confirmación. Contacta al soporte.', 'warning')
            
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash('Error al registrar el usuario: ' + str(e), 'danger')
            return redirect(url_for('registro'))
        finally:
            cursor.close()
            conn.close()
    
    return render_template('registro.html')


@app.route('/confirmar/<token>')
def confirmar(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT usuario_id FROM USUARIO WHERE token = %s AND confirmado = 0", (token,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("UPDATE USUARIO SET confirmado = 1, token = NULL WHERE token = %s", (token,))
            conn.commit()
            flash('Cuenta confirmada exitosamente! Ahora puedes iniciar sesión.', 'success')
        else:
            flash('Token inválido o cuenta ya confirmada', 'danger')
    except Exception as e:
        conn.rollback()
        flash('Error al confirmar la cuenta: ' + str(e), 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('login'))

@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        email = request.form.get('email')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT usuario_id FROM USUARIO WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            # Generar token de recuperación
            token = secrets.token_hex(8)
            
            try:
                cursor.execute("UPDATE USUARIO SET token = %s WHERE email = %s", (token, email))
                conn.commit()
                
                # Enviar email con enlace para restablecer contraseña
                send_reset_email(email, token)
                
                flash('Se ha enviado un enlace a tu correo para restablecer tu contraseña', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                conn.rollback()
                flash('Error al procesar la solicitud: ' + str(e), 'danger')
            finally:
                cursor.close()
                conn.close()
        else:
            flash('No existe una cuenta con ese correo electrónico', 'danger')
            cursor.close()
            conn.close()
    
    return render_template('recuperar.html')

def send_reset_email(email, token):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg['Subject'] = "Restablecer contraseña - BLANK concept"
        
        reset_url = f"http://localhost:5000/restablecer/{token}"
        body = f"""
        <h2>Solicitud de restablecimiento de contraseña</h2>
        <p>Para restablecer tu contraseña, haz clic en el siguiente enlace:</p>
        <a href="{reset_url}">Restablecer contraseña</a>
        <p>Si no solicitaste este cambio, por favor ignora este mensaje.</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error al enviar email de recuperación: {e}")
        return False

@app.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer(token):
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('restablecer', token=token))
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('restablecer', token=token))
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT usuario_id FROM USUARIO WHERE token = %s", (token,))
            user = cursor.fetchone()
            
            if user:
                cursor.execute(
                    "UPDATE USUARIO SET contraseña = %s, token = NULL WHERE token = %s",
                    (hashed_password, token)
                )
                conn.commit()
                flash('Contraseña actualizada exitosamente! Ahora puedes iniciar sesión.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Token inválido o expirado', 'danger')
        except Exception as e:
            conn.rollback()
            flash('Error al actualizar la contraseña: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('restablecer.html', token=token)

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('home'))

#--------------------------------------------------------------------------------------------------------------------
# ACCEDER A LOS PANELES DE LOS DIFERENTES ROLES
#---------------------------------------------------------------------------------------------------------------------
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    return render_template('admin_dashboard.html')

@app.route('/barbero/dashboard')
@login_required
def barber_dashboard():
    if session.get('user_role') != 2:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1) Barbero logueado
    cursor.execute("""
        SELECT b.barbero_id, u.nombre, u.apellido, b.foto_perfil, b.biografia
        FROM Barbero b
        JOIN USUARIO u ON b.usuario_id = u.usuario_id
        WHERE u.usuario_id = %s
    """, (session['user_id'],))
    barbero = cursor.fetchone()

    # 2) Citas de hoy
    hoy = date.today()
    cursor.execute("""
        SELECT c.cita_id, TIME_FORMAT(c.hora, '%H:%i') AS hora, c.estado,
               u.nombre AS cliente_nombre, u.apellido AS cliente_apellido, 
               u.telefono, u.email,
               GROUP_CONCAT(s.nombre SEPARATOR ', ') AS servicios
        FROM CITA c
        JOIN USUARIO u ON c.usuario_id = u.usuario_id
        LEFT JOIN Cita_servicio cs ON c.cita_id = cs.cita_id
        LEFT JOIN Servicios s ON cs.servicio_id = s.servicio_id
        WHERE c.barbero_id = %s AND c.fecha = %s
        GROUP BY c.cita_id
        ORDER BY c.hora ASC
    """, (barbero['barbero_id'], hoy))
    citas_hoy = cursor.fetchall()
    cursor.close(); conn.close()

    # 3) NUEVO: slots del día
    slots_hoy = generar_slots_dia(barbero['barbero_id'], hoy)

    return render_template('barber_dashboard.html',
                           barbero=barbero,
                           citas_hoy=citas_hoy,
                           hoy=hoy,
                           slots_hoy=slots_hoy)

@app.route('/cliente/dashboard')
@login_required
def client_dashboard():
    return redirect(url_for('home'))

#------------------------------------------------------------------------------------------------------------------------------------
# PANEL DE SERVICIOS(MOSTRAR)
#---------------------------------------------------------------------------------------------------------------------------------------
@app.route('/servicios')
def servicios():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener servicios normales
    cursor.execute("SELECT * FROM servicios WHERE tipo_servicio = 'servicio' ORDER BY nombre")
    servicios_normales = cursor.fetchall()
    
    # Obtener combos
    cursor.execute("SELECT * FROM servicios WHERE tipo_servicio = 'combos' ORDER BY nombre")
    servicios_combos = cursor.fetchall()
    
    # Obtener extras
    cursor.execute("SELECT * FROM servicios WHERE tipo_servicio = 'extras' ORDER BY nombre")
    servicios_extras = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('servicios.html', 
                         servicios_normales=servicios_normales,
                         servicios_combos=servicios_combos,
                         servicios_extras=servicios_extras)


#--------------------------------------------------------------------------------------------------------------------
# GESTIÓN DE SERVICIOS
#--------------------------------------------------------------------------------------------------------------------

@app.route('/admin/servicios')
@login_required
def admin_servicios():
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM servicios")
    servicios = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_servicios.html', servicios=servicios)

@app.route('/admin/servicios/agregar', methods=['GET', 'POST'])
@login_required
def agregar_servicio(): #FUNCION PARA AGREGAR SERVICIOS
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        tipo_servicio = request.form.get('tipo_servicio')
        precio = request.form.get('precio')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO servicios (nombre, descripcion, tipo_servicio, precio) VALUES (%s, %s, %s, %s)",
                (nombre, descripcion, tipo_servicio, precio)
            )
            conn.commit()
            flash('Servicio agregado exitosamente', 'success')
            return redirect(url_for('admin_servicios'))
        except Exception as e:
            conn.rollback()
            flash('Error al agregar el servicio: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('agregar_servicio.html')

@app.route('/admin/servicios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_servicio(id): #Funcion para modificar/editar un servicio
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        tipo_servicio = request.form.get('tipo_servicio')
        precio = request.form.get('precio')
        
        try:
            cursor.execute(
                "UPDATE servicios SET nombre = %s, descripcion = %s, tipo_servicio = %s, precio = %s WHERE servicio_id = %s",
                (nombre, descripcion, tipo_servicio, precio, id)
            )
            conn.commit()
            flash('Servicio actualizado exitosamente', 'success')
            return redirect(url_for('admin_servicios'))
        except Exception as e:
            conn.rollback()
            flash('Error al actualizar el servicio: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        try:
            cursor.execute("SELECT * FROM servicios WHERE servicio_id = %s", (id,))
            servicio = cursor.fetchone()
            if not servicio:
                flash('Servicio no encontrado', 'danger')
                return redirect(url_for('admin_servicios'))
            
            return render_template('editar_servicio.html', servicio=servicio)
        finally:
            cursor.close()
            conn.close()

@app.route('/admin/servicios/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_servicio(id): #Eleiminar servicio (Version que puede cambiar en un futuro)
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM servicios WHERE servicio_id = %s", (id,))
        conn.commit()
        flash('Servicio eliminado exitosamente', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error al eliminar el servicio: ' + str(e), 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin_servicios'))

#--------------------------------------------------------------------------------------------------------------------
# AGENDAMIENTO DE CITAS
#--------------------------------------------------------------------------------------------------------------------
@app.route('/reservar_cita', methods=['GET', 'POST'])
@login_required
def reservar_cita():
    servicio_inicial_id = request.args.get('servicio_id')
    barbero_inicial_id  = request.args.get('barbero_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener servicios
    cursor.execute("SELECT * FROM servicios WHERE tipo_servicio = 'servicio' ORDER BY nombre")
    servicios_normales = cursor.fetchall()
    
    cursor.execute("SELECT * FROM servicios WHERE tipo_servicio = 'combos' ORDER BY nombre")
    servicios_combos = cursor.fetchall()
    
    cursor.execute("SELECT * FROM servicios WHERE tipo_servicio = 'extras' ORDER BY nombre")
    servicios_extras = cursor.fetchall()
    
    # Obtener barberos activos
    cursor.execute("""
        SELECT b.barbero_id, u.nombre, u.apellido, b.foto_perfil 
        FROM Barbero b 
        JOIN USUARIO u ON b.usuario_id = u.usuario_id 
        WHERE b.estado = 1
        ORDER BY u.nombre, u.apellido
    """)
    barberos = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template(
        'reservar_cita.html',
        servicios_normales=servicios_normales,
        servicios_combos=servicios_combos,
        servicios_extras=servicios_extras,
        barberos=barberos,
        servicio_inicial_id=servicio_inicial_id,
        barbero_inicial_id=barbero_inicial_id, 
        min_date=date.today().isoformat()
    )


@app.route('/obtener_horarios_disponibles', methods=['POST'])
@login_required
def obtener_horarios_disponibles():
    try:
        fecha = request.form.get('fecha')
        barbero_id = request.form.get('barbero_id')
        
        if not fecha or not barbero_id:
            return jsonify({'error': 'Faltan parámetros requeridos'}), 400
        
        # Convertir la fecha seleccionada
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        hoy = date.today()
        ahora = datetime.now().time()  # hora actual

        #Obtener horario del día (normal o especial)
        horario_dia = obtener_horario_dia(fecha_obj)

        if horario_dia.get('cerrado'):
            return jsonify({
                'horarios': [],
                'cerrado': True,
                'mensaje': 'La barbería estará cerrada este día.'
            })

        hora_inicio = horario_dia['hora_inicio']
        hora_fin = horario_dia['hora_fin']

        inicio_dt = datetime.combine(date.today(), hora_inicio)
        fin_dt = datetime.combine(date.today(), hora_fin)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Citas ya ocupadas
        cursor.execute("""
            SELECT TIME_FORMAT(hora, '%H:%i') as hora_str 
            FROM CITA 
            WHERE barbero_id = %s AND fecha = %s AND estado IN ('pendiente', 'confirmada')
        """, (barbero_id, fecha))
        citas_existentes = [c['hora_str'] for c in cursor.fetchall()]

        horarios_disponibles = []
        actual = inicio_dt
        while actual < fin_dt:
            horario = actual.strftime("%H:%M")

            # Ignorar horarios pasados si es hoy
            if fecha_obj == hoy and actual.time() <= ahora:
                actual += timedelta(minutes=30)
                continue

            if horario not in citas_existentes:
                horarios_disponibles.append(horario)

            actual += timedelta(minutes=30)

        cursor.close()
        conn.close()

        # Si ya no hay horarios disponibles para hoy
        if fecha_obj == hoy and not horarios_disponibles:
            return jsonify({'horarios': [], 'cerrado': True})

        return jsonify({'horarios': horarios_disponibles})

    except Exception as e:
        print(f"ERROR en obtener_horarios_disponibles: {str(e)}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500


@app.route('/procesar_cita', methods=['POST'])
@login_required
def procesar_cita():
    try:
        barbero_id = request.form.get('barbero_id')
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        servicios_seleccionados = request.form.getlist('servicios[]')

        if not all([barbero_id, fecha, hora, servicios_seleccionados]):
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('reservar_cita'))

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1) Inserción atómica: sólo inserta si NO existe una cita activa del usuario ese día
        insert_sql = """
            INSERT INTO CITA (usuario_id, barbero_id, fecha, hora, estado)
            SELECT %s, %s, %s, %s, 'pendiente'
            FROM DUAL
            WHERE NOT EXISTS (
                SELECT 1
                FROM CITA
                WHERE usuario_id = %s
                  AND fecha = %s
                  AND estado IN ('pendiente','confirmada')
            )
        """
        params = (session['user_id'], barbero_id, fecha, hora, session['user_id'], fecha)
        cursor.execute(insert_sql, params)

        if cursor.rowcount == 0:
            # No se insertó por existir ya una cita activa ese día
            conn.rollback()
            flash('Ya tienes una cita agendada para esta fecha. Solo puedes tener una cita por día.', 'danger')
            return redirect(url_for('reservar_cita'))

        cita_id = cursor.lastrowid

        # 2) Insertar servicios de la cita
        for servicio_id in servicios_seleccionados:
            cursor.execute(
                "INSERT INTO Cita_servicio (cita_id, servicio_id) VALUES (%s, %s)",
                (cita_id, servicio_id)
            )

        conn.commit()
        cursor.close()
        conn.close()

        flash('¡Cita reservada exitosamente! Te esperamos en la fecha y hora seleccionada.', 'success')
        return redirect(url_for('mis_citas'))

    except mysql.connector.IntegrityError as ie:
        # Por ejemplo: choque con UNIQUE(barbero_id, fecha, hora)
        if 'uniq_barbero_slot' in str(ie).lower():
            flash('Ese horario ya fue tomado para ese barbero. Elige otra hora.', 'danger')
        else:
            flash('No se pudo reservar por una restricción de base de datos.', 'danger')
        if 'conn' in locals():
            conn.rollback(); cursor.close(); conn.close()
        return redirect(url_for('reservar_cita'))
    except Exception as e:
        if 'conn' in locals():
            conn.rollback(); cursor.close(); conn.close()
        flash('Error al procesar la cita: ' + str(e), 'danger')
        return redirect(url_for('reservar_cita'))


@app.route('/verificar_cita_usuario', methods=['POST'])
@login_required
def verificar_cita_usuario():
    try:
        fecha = request.form.get('fecha')
        if not fecha:
            return jsonify({'error': 'Fecha no proporcionada'}), 400
        
        tiene_cita = usuario_tiene_cita_para_fecha(session['user_id'], fecha)
        return jsonify({'tiene_cita': tiene_cita})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def usuario_tiene_cita_para_fecha(usuario_id, fecha, conn_ext=None):
    """
    True si el usuario ya tiene una cita ACTIVA (pendiente/confirmada) ese día.
    """
    close_after = False
    if conn_ext is None:
        conn = get_db_connection()
        close_after = True
    else:
        conn = conn_ext

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 1
            FROM CITA
            WHERE usuario_id = %s
              AND fecha = %s
              AND estado IN ('pendiente','confirmada')
            LIMIT 1
        """, (usuario_id, fecha))
        return cursor.fetchone() is not None
    except Exception as e:
        print(f"Error al verificar cita existente: {e}")
        return True 
    finally:
        cursor.close()
        if close_after:
            conn.close()


@app.route('/cancelar_cita', methods=['POST'])
@login_required
def cancelar_cita():
    try:
        cita_id = request.form.get('cita_id')
        motivo = request.form.get('motivo')

        if not motivo:
            flash('Debes seleccionar un motivo de cancelación', 'danger')
            return redirect(url_for('mis_citas'))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar que la cita pertenece al usuario actual
        cursor.execute("SELECT usuario_id FROM CITA WHERE cita_id = %s", (cita_id,))
        cita = cursor.fetchone()

        if not cita or cita[0] != session['user_id']:
            flash('No tienes permiso para cancelar esta cita', 'danger')
            return redirect(url_for('mis_citas'))

        # Actualizar el estado de la cita
        cursor.execute("UPDATE CITA SET estado = 'cancelada' WHERE cita_id = %s", (cita_id,))

        # Registrar en la tabla Cancelacion
        cursor.execute("""
            INSERT INTO Cancelacion (cita_id, motivo, cancelado_por)
            VALUES (%s, %s, %s)
        """, (cita_id, motivo, 'cliente'))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Cita cancelada exitosamente', 'success')
        return redirect(url_for('mis_citas'))

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cursor.close()
            conn.close()
        flash('Error al cancelar la cita: ' + str(e), 'danger')
        return redirect(url_for('mis_citas'))



@app.route('/mis_citas')
@login_required
def mis_citas():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener citas del usuario
    cursor.execute("""
        SELECT c.cita_id, c.fecha, c.hora, c.estado,
               u.nombre as barbero_nombre, u.apellido as barbero_apellido,
               GROUP_CONCAT(s.nombre SEPARATOR ', ') as servicios
        FROM CITA c
        JOIN Barbero b ON c.barbero_id = b.barbero_id
        JOIN USUARIO u ON b.usuario_id = u.usuario_id
        LEFT JOIN Cita_servicio cs ON c.cita_id = cs.cita_id
        LEFT JOIN Servicios s ON cs.servicio_id = s.servicio_id
        WHERE c.usuario_id = %s
        GROUP BY c.cita_id
        ORDER BY FIELD(c.estado, 'confirmada','pendiente','completada','cancelada'),
                c.fecha DESC,
                c.hora DESC
    """, (session['user_id'],))
    
    citas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('mis_citas.html', citas=citas)

# ------ VER BARBEROS ------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route('/barberos')
def ver_barberos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            b.barbero_id,
            b.biografia,
            b.foto_perfil,
            u.nombre,
            u.apellido
        FROM Barbero b
        JOIN USUARIO u ON b.usuario_id = u.usuario_id
        WHERE b.estado = 1       -- solo barberos activos
        ORDER BY u.nombre, u.apellido
    """)
    barberos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('barberos.html', barberos=barberos)

"""""
----------------------------------------------------------------------------------MODULO DE BARBERO---------------------------------------------------------------------------------------------------------------
"""

# PERFIL DEL BARBERO (DESCRIPCION Y FOTO)

# Configuración para las imágenes de perfil
UPLOAD_FOLDER = os.path.join("static", "uploads", "barberos")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Crear carpeta si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/barbero/perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil_barbero():
    if session.get('user_role') != 2:  # Solo barberos
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Buscar datos del barbero logueado
    cursor.execute("""
        SELECT b.barbero_id, b.biografia, b.foto_perfil, u.nombre, u.apellido
        FROM Barbero b
        JOIN USUARIO u ON b.usuario_id = u.usuario_id
        WHERE u.usuario_id = %s
    """, (session['user_id'],))
    barbero = cursor.fetchone()

    if request.method == 'POST':
        biografia = request.form.get('biografia')
        foto = request.files.get('foto_perfil')

        if len(biografia) > 60:
            flash('La biografía no puede superar los 60 caracteres', 'danger')
            return redirect(url_for('editar_perfil_barbero'))

        # Si subió una foto válida
        filename = barbero['foto_perfil']  # mantener la actual por defecto
        if foto and allowed_file(foto.filename):
            # Generar nombre único
            ext = foto.filename.rsplit(".", 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(filename))
            foto.save(filepath)

        try:
            cursor.execute("""
                UPDATE Barbero 
                SET biografia = %s, foto_perfil = %s
                WHERE barbero_id = %s
            """, (biografia, filename, barbero['barbero_id']))
            conn.commit()
            flash('Perfil actualizado exitosamente', 'success')
            return redirect(url_for('editar_perfil_barbero'))
        except Exception as e:
            conn.rollback()
            flash('Error al actualizar el perfil: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
    
    cursor.close()
    conn.close()
    return render_template('barbero_perfil.html', barbero=barbero)

# APARTADO PARA CAMBIAR EL ESTADO DE LA CITA

@app.route('/barbero/cambiar_estado_cita', methods=['POST'])
@login_required
def cambiar_estado_cita():
    if session.get('user_role') != 2:
        return jsonify({'error': 'No autorizado'}), 403

    cita_id = request.form.get('cita_id')
    nuevo_estado = request.form.get('estado')

    if nuevo_estado not in ['confirmada', 'cancelada']:
        return jsonify({'error': 'Estado inválido'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar que la cita pertenece al barbero logueado
        cursor.execute("""
            SELECT c.cita_id 
            FROM CITA c
            JOIN Barbero b ON c.barbero_id = b.barbero_id
            WHERE c.cita_id = %s AND b.usuario_id = %s
        """, (cita_id, session['user_id']))
        cita = cursor.fetchone()

        if not cita:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Cita no encontrada o no autorizada'}), 404

        # Actualizar estado
        cursor.execute("UPDATE CITA SET estado = %s WHERE cita_id = %s", (nuevo_estado, cita_id))
        conn.commit()

        return jsonify({'success': True, 'estado': nuevo_estado})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# CANCELACION DE CITA (DESDE EL BARBERO)
@app.route('/barbero/cancelar_cita', methods=['POST'])
@login_required
def barbero_cancelar_cita():
    if session.get('user_role') != 2:  # Solo barberos
        flash('No tienes permiso para esta acción', 'danger')
        return redirect(url_for('client_dashboard'))

    cita_id = request.form.get('cita_id')
    motivo = request.form.get('motivo')

    if not motivo or len(motivo.strip()) == 0:
        flash('Debes escribir un motivo para cancelar la cita.', 'danger')
        return redirect(url_for('barber_dashboard'))

    if len(motivo) > 255:
        flash('El motivo no puede superar los 255 caracteres.', 'danger')
        return redirect(url_for('barber_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar que la cita pertenece al barbero logueado
        cursor.execute("""
            SELECT c.cita_id 
            FROM CITA c
            JOIN Barbero b ON c.barbero_id = b.barbero_id
            WHERE c.cita_id = %s AND b.usuario_id = %s
        """, (cita_id, session['user_id']))
        cita = cursor.fetchone()

        if not cita:
            flash('No tienes permiso para cancelar esta cita', 'danger')
            return redirect(url_for('barber_dashboard'))

        # Cambiar estado de la cita
        cursor.execute("UPDATE CITA SET estado = 'cancelada' WHERE cita_id = %s", (cita_id,))

        # Guardar motivo en Cancelacion
        cursor.execute("""
            INSERT INTO Cancelacion (cita_id, motivo, cancelado_por)
            VALUES (%s, %s, 'barbero')
        """, (cita_id, motivo))

        conn.commit()
        flash('Cita cancelada exitosamente con motivo registrado.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al cancelar la cita: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('barber_dashboard'))

# PARA QUE EL BARBERO PUEDA VER SUS CITAS FUTURAS
@app.route('/barbero/agenda')
@login_required
def barbero_agenda():
    if session.get('user_role') != 2:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Obtener datos del barbero logueado
    cursor.execute("""
        SELECT b.barbero_id, u.nombre, u.apellido
        FROM Barbero b
        JOIN USUARIO u ON b.usuario_id = u.usuario_id
        WHERE u.usuario_id = %s
    """, (session['user_id'],))
    barbero = cursor.fetchone()

    if not barbero:
        flash("No se encontró información del barbero", "danger")
        return redirect(url_for("barber_dashboard"))

    # 2. Obtener citas FUTURAS (mañana en adelante)
    hoy = date.today()
    cursor.execute("""
        SELECT c.cita_id, c.fecha, TIME_FORMAT(c.hora, '%H:%i') AS hora, c.estado,
               u.nombre AS cliente_nombre, u.apellido AS cliente_apellido, 
               u.telefono, u.email,
               GROUP_CONCAT(s.nombre SEPARATOR ', ') AS servicios
        FROM CITA c
        JOIN USUARIO u ON c.usuario_id = u.usuario_id
        LEFT JOIN Cita_servicio cs ON c.cita_id = cs.cita_id
        LEFT JOIN Servicios s ON cs.servicio_id = s.servicio_id
        WHERE c.barbero_id = %s AND c.fecha > %s
        GROUP BY c.cita_id
        ORDER BY c.fecha ASC, c.hora ASC
    """, (barbero['barbero_id'], hoy))

    citas_futuras = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("barbero_agenda.html", barbero=barbero, citas_futuras=citas_futuras)

# --- NUEVO: helpers de slots para el día ---
def generar_slots_dia(barbero_id, fecha_obj):
    """
    Devuelve un dict con:
      - cerrado: bool
      - desde: 'HH:MM' o None
      - hasta: 'HH:MM' o None
      - slots: lista de {hora:'HH:MM', estado:'disponible'|'reservado'|'pasado'}
    """
    horario = obtener_horario_dia(fecha_obj)  # ya maneja horarios especiales/cerrado
    if horario.get('cerrado'):
        return {'cerrado': True, 'desde': None, 'hasta': None, 'slots': []}

    desde_dt = datetime.combine(fecha_obj, horario['hora_inicio'])
    hasta_dt = datetime.combine(fecha_obj, horario['hora_fin'])

    # Buscar horas ya ocupadas por ese barbero hoy (pendiente/confirmada)
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT TIME_FORMAT(hora, '%H:%i') AS h
        FROM CITA
        WHERE barbero_id = %s AND fecha = %s AND estado IN ('pendiente','confirmada')
    """, (barbero_id, fecha_obj))
    ocupadas = {row['h'] for row in cur.fetchall()}
    cur.close(); conn.close()

    ahora_time = datetime.now().time()
    slots = []
    actual = desde_dt
    while actual < hasta_dt:
        hhmm = actual.strftime('%H:%M')
        if fecha_obj == date.today() and actual.time() <= ahora_time:
            estado = 'pasado'
        elif hhmm in ocupadas:
            estado = 'reservado'
        else:
            estado = 'disponible'
        slots.append({'hora': hhmm, 'estado': estado})
        actual += timedelta(minutes=30)

    return {
        'cerrado': False,
        'desde': horario['hora_inicio'].strftime('%H:%M'),
        'hasta': horario['hora_fin'].strftime('%H:%M'),
        'slots': slots
    }





"""""
-------------------------------------------------------------------------------MODULO ADMINISTRADOR---------------------------------------------------------------------------
"""

#--------------------------------------------------------------------------------------------------------------------
# REGISTRAR BARBERO EN ADMINISTRADOR
#--------------------------------------------------------------------------------------------------------------------

# Agregar esta ruta después de las otras rutas de administrador
@app.route('/admin/barberos/registrar', methods=['GET', 'POST'])
@login_required
def registrar_barbero():
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        segundo_nombre = request.form.get('segundo_nombre')
        apellido = request.form.get('apellido')
        segundo_apellido = request.form.get('segundo_apellido')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        fecha_contratacion = request.form.get('fecha_contratacion')
        
        # Validaciones básicas
        if not all([nombre, segundo_nombre, apellido, segundo_apellido, email, fecha_contratacion]):
            flash('Todos los campos obligatorios deben ser completados', 'danger')
            return redirect(url_for('registrar_barbero'))
        
        # Contraseña por defecto
        password_temp = "123456"
        hashed_password = generate_password_hash(password_temp)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verificar si el email ya existe
            cursor.execute("SELECT email FROM USUARIO WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Este correo electrónico ya está registrado', 'danger')
                return redirect(url_for('registrar_barbero'))
            
            # Insertar nuevo usuario con rol de barbero (rol=2)
            cursor.execute(
                "INSERT INTO USUARIO (nombre, segundo_nombre, apellido, segundo_apellido, email, telefono, contraseña, rol, confirmado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (nombre, segundo_nombre, apellido, segundo_apellido, email, telefono, hashed_password, 2, 1)  # confirmado=1 para no requerir confirmación
            )
            usuario_id = cursor.lastrowid
            
            # Insertar en la tabla Barbero
            cursor.execute(
                "INSERT INTO Barbero (usuario_id, fecha_contratacion, estado) VALUES (%s, %s, %s)",
                (usuario_id, fecha_contratacion, 1)  # estado=1 (activo)
            )
            
            conn.commit()
            
            # Enviar email de notificación
            if enviar_email_registro_barbero(email, f"{nombre} {apellido}", password_temp):
                flash(f'Barbero registrado exitosamente! Se ha enviado un email con las credenciales a {email}', 'success')
            else:
                flash(f'Barbero registrado exitosamente! Contraseña temporal: {password_temp} (No se pudo enviar el email)', 'warning')
            
            return redirect(url_for('registrar_barbero'))
            
        except Exception as e:
            conn.rollback()
            flash('Error al registrar el barbero: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('registrar_barbero.html')

# Editar información de barbero
@app.route('/admin/barberos/editar/<int:barbero_id>', methods=['GET', 'POST'])
@login_required
def editar_barbero(barbero_id):
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        fecha_contratacion = request.form.get('fecha_contratacion')
        
        try:
            # Verificar si el email ya existe en otro usuario
            cursor.execute(
                "SELECT usuario_id FROM USUARIO WHERE email = %s AND usuario_id != (SELECT usuario_id FROM Barbero WHERE barbero_id = %s)",
                (email, barbero_id)
            )
            if cursor.fetchone():
                flash('Este correo electrónico ya está registrado por otro usuario', 'danger')
                return redirect(url_for('editar_barbero', barbero_id=barbero_id))
            
            # Actualizar información del usuario
            cursor.execute(
                """UPDATE USUARIO SET 
                    nombre = %s, 
                    apellido = %s, 
                    email = %s, 
                    telefono = %s 
                WHERE usuario_id = (SELECT usuario_id FROM Barbero WHERE barbero_id = %s)""",
                (nombre, apellido, email, telefono, barbero_id)
            )
            
            # Actualizar información específica del barbero
            cursor.execute(
                "UPDATE Barbero SET fecha_contratacion = %s WHERE barbero_id = %s",
                (fecha_contratacion, barbero_id)
            )
            
            conn.commit()
            flash('Información del barbero actualizada exitosamente', 'success')
            return redirect(url_for('listar_barberos'))
            
        except Exception as e:
            conn.rollback()
            flash('Error al actualizar el barbero: ' + str(e), 'danger')
            return redirect(url_for('editar_barbero', barbero_id=barbero_id))
        finally:
            cursor.close()
            conn.close()
    else:
        try:
            # Obtener información del barbero
            cursor.execute("""
                SELECT u.usuario_id, u.nombre, u.apellido, u.email, u.telefono, 
                       b.barbero_id, b.fecha_contratacion, b.estado
                FROM USUARIO u
                JOIN Barbero b ON u.usuario_id = b.usuario_id
                WHERE b.barbero_id = %s
            """, (barbero_id,))
            barbero = cursor.fetchone()
            
            if not barbero:
                flash('Barbero no encontrado', 'danger')
                return redirect(url_for('listar_barberos'))
            
            return render_template('editar_barbero.html', barbero=barbero)
        except Exception as e:
            flash('Error al obtener información del barbero: ' + str(e), 'danger')
            return redirect(url_for('listar_barberos'))
        finally:
            cursor.close()
            conn.close()

# Lista de barberos
@app.route('/admin/barberos')
@login_required
def listar_barberos():
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Consulta para obtener todos los barberos con su información de usuario
        cursor.execute("""
            SELECT u.usuario_id, u.nombre, u.apellido, u.email, u.telefono, 
                   b.barbero_id, b.fecha_contratacion, b.estado
            FROM USUARIO u
            JOIN Barbero b ON u.usuario_id = b.usuario_id
            ORDER BY u.nombre, u.apellido
        """)
        barberos = cursor.fetchall()
    except Exception as e:
        flash('Error al obtener la lista de barberos: ' + str(e), 'danger')
        barberos = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('listar_barberos.html', barberos=barberos)

# Cambiar estado del barbero
@app.route('/admin/barberos/cambiar_estado/<int:barbero_id>', methods=['POST'])
@login_required
def cambiar_estado_barbero(barbero_id):
    if session.get('user_role') != 1:
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('client_dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener el estado actual
        cursor.execute("SELECT estado FROM Barbero WHERE barbero_id = %s", (barbero_id,))
        barbero = cursor.fetchone()
        
        if not barbero:
            flash('Barbero no encontrado', 'danger')
            return redirect(url_for('listar_barberos'))
        
        nuevo_estado = 1 if barbero['estado'] == 0 else 0
        
        # Actualizar estado
        cursor.execute(
            "UPDATE Barbero SET estado = %s WHERE barbero_id = %s",
            (nuevo_estado, barbero_id)
        )
        conn.commit()
        
        estado_texto = "activado" if nuevo_estado == 1 else "desactivado"
        flash(f'Estado del barbero actualizado: {estado_texto}', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error al cambiar el estado del barbero: ' + str(e), 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('listar_barberos'))

# Función para enviar email de notificación al barbero
def enviar_email_registro_barbero(email, nombre, password_temp):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg['Subject'] = "Bienvenido a BLANK concept - Tus credenciales de acceso"
        
        body = f"""
        <h2>¡Bienvenido {nombre}!</h2>
        <p>Has sido registrado como barbero en BLANK concept.</p>
        <p>Tus credenciales de acceso son:</p>
        <ul>
            <li><strong>Email:</strong> {email}</li>
            <li><strong>Contraseña temporal:</strong> {password_temp}</li>
        </ul>
        <p>Por seguridad, te recomendamos cambiar tu contraseña después de iniciar sesión por primera vez.</p>
        <p>Puedes acceder al sistema aquí: <a href="http://localhost:5000/login">Iniciar sesión</a></p>
        <p>Si no reconoces este registro, por favor contacta al administrador.</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error al enviar email de registro: {e}")
        return False

# ---------------------- ADMIN: LISTADO DE TODAS LAS CITAS ----------------------

@app.route('/admin/citas')
@login_required
def admin_citas():
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))

    # --- filtros ---
    fecha_inicio = request.args.get('fecha_inicio')  # 'YYYY-MM-DD'
    fecha_fin = request.args.get('fecha_fin')        # 'YYYY-MM-DD'
    estado = request.args.get('estado')              # pendiente, confirmada, completada, cancelada, no asistio
    barbero_id = request.args.get('barbero_id')      # int

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Para el selector de barberos
    cursor.execute("""
        SELECT b.barbero_id, u.nombre, u.apellido
        FROM Barbero b
        JOIN USUARIO u ON b.usuario_id = u.usuario_id
        ORDER BY u.nombre, u.apellido
    """)
    barberos = cursor.fetchall()

    # Construir SQL con filtros dinámicos
    query = """
    SELECT 
        c.cita_id,
        c.fecha,
        TIME_FORMAT(c.hora, '%H:%i') AS hora,
        c.estado,
        uc.nombre  AS cliente_nombre,
        uc.apellido AS cliente_apellido,
        ub.nombre  AS barbero_nombre,
        ub.apellido AS barbero_apellido,
        GROUP_CONCAT(s.nombre ORDER BY s.nombre SEPARATOR ', ') AS servicios,
        can.motivo AS motivo_cancelacion,
        can.fecha_cancelacion,
        can.cancelado_por
    FROM CITA c
    JOIN USUARIO uc         ON c.usuario_id = uc.usuario_id
    JOIN Barbero b          ON c.barbero_id = b.barbero_id
    JOIN USUARIO ub         ON b.usuario_id = ub.usuario_id
    LEFT JOIN Cita_servicio cs ON c.cita_id = cs.cita_id
    LEFT JOIN Servicios s      ON cs.servicio_id = s.servicio_id
    /* ÚLTIMA cancelación por cita (si existiera) */
    LEFT JOIN (
        SELECT c1.*
        FROM Cancelacion c1
        JOIN (
            SELECT cita_id, MAX(fecha_cancelacion) AS max_fecha
            FROM Cancelacion
            GROUP BY cita_id
        ) c2 
          ON c1.cita_id = c2.cita_id 
         AND c1.fecha_cancelacion = c2.max_fecha
    ) can ON can.cita_id = c.cita_id
    WHERE 1=1
    """
    params = []

    if fecha_inicio:
        query += " AND c.fecha >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND c.fecha <= %s"
        params.append(fecha_fin)
    if estado and estado != 'todos':
        query += " AND c.estado = %s"
        params.append(estado)
    if barbero_id and barbero_id.isdigit():
        query += " AND c.barbero_id = %s"
        params.append(int(barbero_id))

    query += """
        GROUP BY c.cita_id
        ORDER BY c.fecha DESC, c.hora DESC
        LIMIT 500
    """  # LIMITE de seguridad

    cursor.execute(query, tuple(params))
    citas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_citas.html',
                           citas=citas,
                           barberos=barberos,
                           filtros=dict(
                               fecha_inicio=fecha_inicio or '',
                               fecha_fin=fecha_fin or '',
                               estado=estado or 'todos',
                               barbero_id=barbero_id or ''
                           ))

@app.route('/admin/citas/exportar')
@login_required
def admin_citas_exportar():
    if session.get('user_role') != 1:
        flash('No tienes permiso para acceder a esta página', 'danger')
        return redirect(url_for('client_dashboard'))

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    estado = request.args.get('estado')
    barbero_id = request.args.get('barbero_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            c.cita_id,
            c.fecha,
            TIME_FORMAT(c.hora, '%H:%i') AS hora,
            c.estado,
            CONCAT(uc.nombre,' ',uc.apellido) AS cliente,85 
            CONCAT(ub.nombre,' ',ub.apellido) AS barbero,
            GROUP_CONCAT(s.nombre ORDER BY s.nombre SEPARATOR ', ') AS servicios,
            COALESCE(can.motivo,'') AS motivo_cancelacion,
            COALESCE(DATE_FORMAT(can.fecha_cancelacion, '%Y-%m-%d %H:%i'), '') AS fecha_cancelacion
        FROM CITA c
        JOIN USUARIO uc         ON c.usuario_id = uc.usuario_id
        JOIN Barbero b          ON c.barbero_id = b.barbero_id
        JOIN USUARIO ub         ON b.usuario_id = ub.usuario_id
        LEFT JOIN Cita_servicio cs ON c.cita_id = cs.cita_id
        LEFT JOIN Servicios s      ON cs.servicio_id = s.servicio_id
        LEFT JOIN Cancelacion can  ON can.cita_id = c.cita_id
        WHERE 1=1
    """
    params = []
    if fecha_inicio:
        query += " AND c.fecha >= %s"; params.append(fecha_inicio)
    if fecha_fin:
        query += " AND c.fecha <= %s"; params.append(fecha_fin)
    if estado and estado != 'todos':
        query += " AND c.estado = %s"; params.append(estado)
    if barbero_id and barbero_id.isdigit():
        query += " AND c.barbero_id = %s"; params.append(int(barbero_id))

    query += " GROUP BY c.cita_id ORDER BY c.fecha DESC, c.hora DESC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    headers = [desc[0] for desc in cursor.description]

    # Crear CSV en memoria
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    for r in rows:
        cw.writerow(r)

    cursor.close(); conn.close()

    output = si.getvalue()
    return app.response_class(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=citas.csv'}
    )

def obtener_horario_dia(fecha_obj):
    """
    Devuelve un diccionario con las horas de apertura y cierre reales del día.
    Soporta TIME en base de datos como str, time o timedelta.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM horario_especial WHERE fecha = %s", (fecha_obj,))
    especial = cursor.fetchone()
    cursor.close()
    conn.close()

    if especial:
        if especial.get('cerrado') == 1:
            return {'cerrado': True}

        hora_inicio = especial.get('hora_apertura')
        hora_fin = especial.get('hora_cierre')

        # ✅ Convertir timedelta → time
        if isinstance(hora_inicio, timedelta):
            segundos = hora_inicio.total_seconds()
            hora_inicio = time(int(segundos // 3600), int((segundos % 3600) // 60))
        if isinstance(hora_fin, timedelta):
            segundos = hora_fin.total_seconds()
            hora_fin = time(int(segundos // 3600), int((segundos % 3600) // 60))

        # ✅ Convertir string → time
        if isinstance(hora_inicio, str):
            try:
                hora_inicio = datetime.strptime(hora_inicio, "%H:%M:%S").time()
            except ValueError:
                hora_inicio = datetime.strptime(hora_inicio, "%H:%M").time()
        if isinstance(hora_fin, str):
            try:
                hora_fin = datetime.strptime(hora_fin, "%H:%M:%S").time()
            except ValueError:
                hora_fin = datetime.strptime(hora_fin, "%H:%M").time()

        return {
            'hora_inicio': hora_inicio,
            'hora_fin': hora_fin,
            'cerrado': False
        }

    # Horario base si no hay especial
    dia_semana = fecha_obj.weekday()
    if dia_semana == 5:  # Sábado
        return {'hora_inicio': time(10, 0), 'hora_fin': time(20, 0), 'cerrado': False}
    elif dia_semana == 6:  # Domingo
        return {'hora_inicio': time(12, 0), 'hora_fin': time(18, 0), 'cerrado': False}
    else:
        return {'hora_inicio': time(12, 0), 'hora_fin': time(21, 0), 'cerrado': False}




@app.route('/admin/horarios', methods=['GET', 'POST'])
@login_required
def admin_horarios():
    if session.get('user_role') != 1:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('client_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        fecha = request.form.get('fecha')
        hora_apertura = request.form.get('hora_apertura')
        hora_cierre = request.form.get('hora_cierre')
        motivo = request.form.get('motivo')
        cerrado = 1 if request.form.get('cerrado') else 0

        try:
            cursor.execute("""
                INSERT INTO horario_especial (fecha, hora_apertura, hora_cierre, cerrado, motivo)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE hora_apertura=VALUES(hora_apertura), hora_cierre=VALUES(hora_cierre),
                                        cerrado=VALUES(cerrado), motivo=VALUES(motivo)
            """, (fecha, hora_apertura, hora_cierre, cerrado, motivo))
            conn.commit()
            flash('Horario guardado correctamente', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error al guardar el horario: {e}', 'danger')

    cursor.execute("SELECT * FROM horario_especial ORDER BY fecha DESC LIMIT 15")
    horarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_horarios.html', horarios=horarios)

@app.route('/admin/horarios/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_horario_especial(id):
    if session.get('user_role') != 1:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('client_dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM horario_especial WHERE id = %s", (id,))
        conn.commit()
        flash('Horario eliminado correctamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al eliminar horario: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_horarios'))





if __name__ == "__main__":
    app.run(debug=True)
// reservar_cita.js (mejorado) - UI de horarios con "chips"
(function () {
  const fecha = document.getElementById('fechaSelect');
  const horaHidden = document.getElementById('horaHidden');
  const horaSelectFallback = document.getElementById('horaSelect'); // respaldo
  const reservarBtn = document.getElementById('btnReservar');
  const slotsContainer = document.getElementById('slotsContainer');
  const slotsGrid = document.getElementById('slotsGrid');
  const slotsMessage = document.getElementById('slotsMessage');
  const slotsLoading = document.getElementById('slotsLoading');
  const cerradoAlert = document.getElementById('cerradoAlert');

  let selectedBarbero = null;
  let selectedSlotBtn = null;

  // Tarjetas de barbero clicables (el input radio está oculto)
  document.querySelectorAll('.barbero-card').forEach(card => {
    card.addEventListener('click', () => {
      const radio = card.closest('label').querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        radio.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
  });

  document.querySelectorAll('.barbero-radio').forEach(r => {
    r.addEventListener('change', () => {
      selectedBarbero = r.value;
      horaHidden.value = '';
      reservarBtn.disabled = true;
      renderEmpty('Selecciona una fecha para ver horarios.');
      if (fecha.value) fetchHorarios();
    });
  });

  if (fecha) {
    fecha.addEventListener('change', () => {
      horaHidden.value = '';
      reservarBtn.disabled = true;
      if (selectedBarbero) fetchHorarios();
      else renderEmpty('Selecciona primero un barbero.');
    });
  }

  function renderEmpty(message) {
    slotsGrid.classList.add('d-none');
    cerradoAlert.classList.add('d-none');
    slotsMessage.textContent = message;
    slotsContainer.querySelector('.slots-empty').classList.remove('d-none');
  }

  function renderLoading() {
    cerradoAlert.classList.add('d-none');
    slotsContainer.querySelector('.slots-empty').classList.remove('d-none');
    slotsLoading.classList.remove('d-none');
    slotsMessage.textContent = 'Cargando horarios...';
    slotsGrid.classList.add('d-none');
  }

  function renderSlots(horasDisponibles) {
    slotsLoading.classList.add('d-none');
    slotsContainer.querySelector('.slots-empty').classList.add('d-none');
    slotsGrid.innerHTML = '';
    slotsGrid.classList.remove('d-none');

    if (!horasDisponibles || horasDisponibles.length === 0) {
      renderEmpty('No hay horarios disponibles. Prueba con otro día.');
      return;
    }

    horasDisponibles.forEach(hhmm => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'slot-btn';
      btn.dataset.time = hhmm;
      btn.setAttribute('role', 'option');
      btn.setAttribute('aria-label', `Hora ${hhmm}`);
      btn.textContent = hhmm;
      btn.addEventListener('click', () => selectSlot(btn));
      slotsGrid.appendChild(btn);
    });
  }

  function selectSlot(btn) {
    if (selectedSlotBtn) selectedSlotBtn.classList.remove('selected');
    selectedSlotBtn = btn;
    btn.classList.add('selected');
    horaHidden.value = btn.dataset.time;
    // mantener el select de respaldo sincronizado, por si el backend lo usa
    syncFallbackSelect(btn.dataset.time);
    reservarBtn.disabled = false;
  }

  function syncFallbackSelect(hhmm) {
    if (!horaSelectFallback) return;
    horaSelectFallback.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = hhmm;
    opt.textContent = hhmm;
    horaSelectFallback.appendChild(opt);
    horaSelectFallback.disabled = false;
  }

  async function fetchHorarios() {
    if (!selectedBarbero || !fecha.value) return;
    try {
      renderLoading();

      const formData = new FormData();
      formData.append('barbero_id', selectedBarbero);
      formData.append('fecha', fecha.value);

      const resp = await fetch('/obtener_horarios_disponibles', {
        method: 'POST',
        body: formData
      });

      if (!resp.ok) throw new Error('No se pudieron cargar los horarios.');
      const data = await resp.json();

      // Manejo de barbería cerrada
      if (data.cerrado) {
        slotsGrid.classList.add('d-none');
        slotsLoading.classList.add('d-none');
        slotsContainer.querySelector('.slots-empty').classList.remove('d-none');
        slotsMessage.textContent = data.mensaje || 'La barbería estará cerrada este día.';
        cerradoAlert.classList.remove('d-none');
        return;
      }

      cerradoAlert.classList.add('d-none');
      renderSlots(data.horarios || []);
    } catch (err) {
      slotsLoading.classList.add('d-none');
      renderEmpty('Ocurrió un error cargando los horarios. Intenta nuevamente.');
      console.error(err);
    }
  }

  // Validación final antes de enviar
  const form = document.getElementById('citaForm');
  if (form) {
    form.addEventListener('submit', (e) => {
      if (!horaHidden.value) {
        e.preventDefault();
        renderEmpty('Debes seleccionar una hora disponible.');
        slotsContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
  }

  // ----- Extras: activar/desactivar extras según servicios seleccionados -----
  const checkboxes = document.querySelectorAll('.servicio-checkbox');
  const extraBoxes = document.querySelectorAll('.servicio-extra');
  const extraAlert = document.getElementById('extra-alert');
  const totalSpan = document.getElementById('totalSeleccionado');

  function updateExtrasAndTotal() {
    let total = 0;
    let baseSelected = false;

    checkboxes.forEach(cb => {
      if (cb.checked) {
        total += parseFloat(cb.getAttribute('data-precio') || '0');
      }
      const type = cb.getAttribute('data-tipo');
      if (cb.checked && (type === 'servicio' || type === 'combo')) baseSelected = true;
    });

    extraBoxes.forEach(cb => {
      cb.disabled = !baseSelected;
      const label = document.querySelector(`label[for="${cb.id}"]`);
      if (label) label.classList.toggle('extra-disabled', !baseSelected);
      if (!baseSelected) cb.checked = false;
    });

    extraAlert.style.display = baseSelected ? 'none' : 'block';
    totalSpan.textContent = `Q${total.toFixed(2)}`;
  }

  checkboxes.forEach(cb => cb.addEventListener('change', updateExtrasAndTotal));
  updateExtrasAndTotal();
   if (window.BARBERO_INICIAL_ID) {
    const rbInicial = document.querySelector(
      `.barbero-radio[value="${window.BARBERO_INICIAL_ID}"]`
    );

    if (rbInicial) {
      rbInicial.checked = true;
      // Usamos el mismo flujo que cuando el usuario hace click
      rbInicial.dispatchEvent(new Event('change', { bubbles: true }));

      const label = rbInicial.closest('label');
      if (label) {
        label.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }

  // --- NUEVO: marcar servicio inicial si viene desde servicios.html ---
  if (window.SERVICIO_INICIAL_ID) {
    const cbInicial = document.querySelector(
      `.servicio-checkbox[value="${window.SERVICIO_INICIAL_ID}"]`
    );

    if (cbInicial) {
      cbInicial.checked = true;        // lo marca
      updateExtrasAndTotal();          // recalcula total y habilita extras
      cbInicial.scrollIntoView({       // opcional: hace scroll hacia el servicio
        behavior: 'smooth',
        block: 'center'
      });
    }
  }
})();
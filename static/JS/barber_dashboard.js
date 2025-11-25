document.addEventListener("DOMContentLoaded", function() {
            const buttons = document.querySelectorAll(".btn-cambiar-estado");

            buttons.forEach(btn => {
                btn.addEventListener("click", function() {
                    const citaId = this.closest(".cambiar-estado-form").dataset.citaId;
                    const nuevoEstado = this.dataset.estado;

                    fetch("/barbero/cambiar_estado_cita", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/x-www-form-urlencoded"
                        },
                        body: `cita_id=${citaId}&estado=${nuevoEstado}`
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            alert(`Estado cambiado a: ${data.estado}`);
                            location.reload(); // refresca para ver cambios
                        } else {
                            alert("Error: " + (data.error || "No se pudo cambiar el estado"));
                        }
                    })
                    .catch(err => {
                        alert("Error del servidor: " + err);
                    });
                });
            });
            
});
// /static/JS/barber_dashboard.js
document.addEventListener("DOMContentLoaded", () => {
  const estadoBtns = document.querySelectorAll(".btn-cambiar-estado");

  const toast = (msg, ok = true) => {
    const el = document.createElement("div");
    el.className = `position-fixed top-0 start-50 translate-middle-x mt-3 alert ${ok ? "alert-success" : "alert-danger"}`;
    el.style.zIndex = 1080;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2200);
  };

  const updateBadges = (root, nuevo) => {
    // Cambia badge de estado dentro del item/modal
    root.querySelectorAll(".estado-badge").forEach(b => {
      b.classList.remove("estado-pendiente","estado-confirmada");
      b.classList.add(`estado-${nuevo}`);
      b.innerHTML = (nuevo === "confirmada" ? '<i class="bi bi-check2-circle me-1"></i>' : '<i class="bi bi-hourglass-split me-1"></i>') + 
                    (nuevo.charAt(0).toUpperCase() + nuevo.slice(1));
    });

    // Oculta botón "Confirmar" si ya quedó confirmada
    if (nuevo === "confirmada") {
      root.querySelectorAll('.btn-cambiar-estado[data-estado="confirmada"]').forEach(b => b.remove());
    }
  };

  estadoBtns.forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const citaId = e.currentTarget.dataset.cita;
      const estado = e.currentTarget.dataset.estado;

      const fd = new FormData();
      fd.append("cita_id", citaId);
      fd.append("estado", estado);

      try {
        const resp = await fetch("/barbero/cambiar_estado_cita", { method:"POST", body: fd });
        const data = await resp.json();

        if (data.success) {
          // Actualiza en el item y también en el modal (si estaba abierto)
          const item = document.querySelector(`[data-cita-item-id="${citaId}"]`) || e.currentTarget.closest(".timeline-item");
          if (item) updateBadges(item, estado);

          const modal = document.querySelector(`#citaModal${citaId}`);
          if (modal) updateBadges(modal, estado);

          toast("Cita actualizada a " + estado);
        } else {
          toast(data.error || "No se pudo cambiar el estado", false);
        }
      } catch (err) {
        console.error(err);
        toast("Error de red al cambiar estado", false);
      }
    });
  });

  // Marca cada timeline-item con data-cita-item-id para updates dirigidos (opcional)
  document.querySelectorAll(".timeline-item").forEach(li => {
    const btn = li.querySelector(".btn-cambiar-estado");
    if (btn) li.setAttribute("data-cita-item-id", btn.dataset.cita);
  });
});
    
// Agenda: filtros, búsqueda y cambio de estado
document.addEventListener("DOMContentLoaded", () => {
  const filterBtns = document.querySelectorAll(".filter-estado .btn");
  const searchInput = document.getElementById("agendaSearch");
  const items = () => Array.from(document.querySelectorAll(".timeline-item"));

  // ---- Toast minimalista ----
  const toast = (msg, ok = true) => {
    const el = document.createElement("div");
    el.className = `position-fixed top-0 start-50 translate-middle-x mt-3 alert ${ok ? "alert-success" : "alert-danger"}`;
    el.style.zIndex = 1080;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2200);
  };

  // ---- Filtros ----
  let currentFilter = "all";
  let currentQuery = "";

  const applyFilters = () => {
    items().forEach(li => {
      const estado = (li.dataset.estado || "").toLowerCase();
      const text = (li.dataset.search || "").toLowerCase();
      const matchesEstado = currentFilter === "all" || estado === currentFilter;
      const matchesSearch = !currentQuery || text.includes(currentQuery);
      li.style.display = (matchesEstado && matchesSearch) ? "" : "none";
    });
  };

  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      applyFilters();
    });
  });

  searchInput?.addEventListener("input", e => {
    currentQuery = e.target.value.trim().toLowerCase();
    applyFilters();
  });

  // ---- Cambiar estado (confirmar) ----
  const updateBadges = (root, nuevo) => {
    root.querySelectorAll(".estado-badge").forEach(b => {
      b.classList.remove("estado-pendiente","estado-confirmada","estado-cancelada");
      b.classList.add(`estado-${nuevo}`);
      b.textContent = nuevo.charAt(0).toUpperCase() + nuevo.slice(1);
    });
    // Actualiza data-estado del item para que el filtro funcione
    root.dataset.estado = nuevo;
    // Quita botón confirmar si ya quedó confirmada
    if (nuevo === "confirmada") {
      root.querySelectorAll('.btn-cambiar-estado[data-estado="confirmada"]').forEach(b => b.remove());
    }
  };

  document.querySelectorAll(".btn-cambiar-estado").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const citaId = e.currentTarget.dataset.cita;
      const estado = e.currentTarget.dataset.estado;

      const fd = new FormData();
      fd.append("cita_id", citaId);
      fd.append("estado", estado);

      try {
        const resp = await fetch("/barbero/cambiar_estado_cita", { method: "POST", body: fd });
        const data = await resp.json();

        if (data.success) {
          // Item en lista
          const item = document.querySelector(`[data-cita-item-id="${citaId}"]`);
          if (item) updateBadges(item, estado);
          // Modal abierto (si existe)
          const modal = document.querySelector(`#citaModal${citaId}`);
          if (modal) updateBadges(modal, estado);
          toast("Cita actualizada a " + estado);
          applyFilters();
        } else {
          toast(data.error || "No se pudo cambiar el estado", false);
        }
      } catch (err) {
        console.error(err);
        toast("Error de red al cambiar estado", false);
      }
    });
  });

  // Inicial
  applyFilters();
});

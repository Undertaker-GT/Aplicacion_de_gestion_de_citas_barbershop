document.addEventListener("DOMContentLoaded", () => {
  const bio = document.getElementById("biografia");
  const counter = document.getElementById("bioCount");
  const fileInput = document.getElementById("foto_perfil");
  const avatar = document.getElementById("avatarPreview");
  const btnCambiar = document.getElementById("btnCambiarFoto");
  const btnLimpiar = document.getElementById("btnLimpiarFoto");

  // --- contador de caracteres ---
  const updateCount = () => {
    const len = bio.value.length;
    counter.textContent = `${len}/60`;
    counter.classList.toggle("text-danger", len > 60);
  };
  updateCount();
  bio.addEventListener("input", updateCount);

  // --- abrir selector de archivos ---
  btnCambiar?.addEventListener("click", () => fileInput.click());

  // --- vista previa ---
  let originalSrc = avatar?.getAttribute("src"); // para restaurar
  fileInput?.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) { alert("Selecciona una imagen válida."); return; }
    const url = URL.createObjectURL(file);
    avatar.src = url;
  });

  // --- limpiar selección (restaurar preview) ---
  btnLimpiar?.addEventListener("click", () => {
    if (fileInput) fileInput.value = "";
    if (avatar && originalSrc) avatar.src = originalSrc;
  });
});

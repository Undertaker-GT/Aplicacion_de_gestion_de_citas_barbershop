document.getElementById('registerForm').addEventListener('submit', function(e) {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const telefono = document.getElementById('telefono').value;
    
    // Validar que las contraseñas coincidan
    if (password !== confirmPassword) {
        e.preventDefault();
        alert('Las contraseñas no coinciden');
        return;
    }
    
    // Validar longitud mínima de contraseña
    if (password.length < 6) {
        e.preventDefault();
        alert('La contraseña debe tener al menos 6 caracteres');
        return;
    }
    
    // Validar formato de teléfono si se proporciona
    if (telefono && !/^\d{8}$/.test(telefono)) {
        e.preventDefault();
        alert('El teléfono debe tener 8 dígitos');
        return;
    }
});
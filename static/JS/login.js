document.getElementById('loginForm').addEventListener('submit', function(e) {
    // Validación básica del lado del cliente
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    if (!email || !password) {
        e.preventDefault();
        alert('Por favor completa todos los campos');
    }
});
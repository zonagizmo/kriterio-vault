export const VERSION = '1.10.00'
// Elimina ceros iniciales de cada componente: 1.01.00 → 1.1.0
export const VERSION_DISPLAY = VERSION.split('.').map(Number).join('.')

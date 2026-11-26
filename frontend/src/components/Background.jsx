// Fondo dividido: cada mitad muestra la foto del tema de una ciudad.
// La capa de la segunda ciudad cubre todo el fondo; la de la primera va encima
// y se desvanece hacia el centro, así las dos fotos se funden sin corte.
export default function Background({ firstImage, secondImage }) {
  return (
    <div className="background" aria-hidden="true">
      <div
        className="background__layer"
        style={{ backgroundImage: `url(${secondImage})` }}
      />
      <div
        className="background__layer background__layer--first"
        style={{ backgroundImage: `url(${firstImage})` }}
      />
    </div>
  );
}

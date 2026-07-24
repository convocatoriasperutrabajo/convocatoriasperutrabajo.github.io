(() => {
  const departamento = document.querySelector("#filtro-departamento");
  const provincia = document.querySelector("#filtro-provincia");
  const distrito = document.querySelector("#filtro-distrito");
  const limpiar = document.querySelector("#limpiar-filtros");
  const contador = document.querySelector("#contador-resultados");
  const vacio = document.querySelector("#resultados-vacios");
  const ofertas = [...document.querySelectorAll(".job-item")];

  if (!departamento || !provincia || !distrito || !limpiar || !contador || !vacio || !ofertas.length) return;

  const secciones = [...document.querySelectorAll(".dep-section")];

  const cargarOpciones = (select, valores, textoInicial) => {
    const anterior = select.value;
    const opciones = [...new Set(valores.filter(Boolean))].sort((a, b) => a.localeCompare(b, "es"));
    const opcionInicial = new Option(textoInicial, "");
    select.replaceChildren(opcionInicial, ...opciones.map((valor) => new Option(valor, valor)));
    select.disabled = opciones.length === 0;
    if (opciones.includes(anterior)) select.value = anterior;
  };

  const actualizarControles = () => {
    const seleccionDepartamento = departamento.value;
    const filasDepartamento = ofertas.filter((oferta) => !seleccionDepartamento || oferta.dataset.departamento === seleccionDepartamento);
    cargarOpciones(provincia, filasDepartamento.map((oferta) => oferta.dataset.provincia), "Todas las provincias o localidades");

    const seleccionProvincia = provincia.value;
    const filasProvincia = filasDepartamento.filter((oferta) => !seleccionProvincia || oferta.dataset.provincia === seleccionProvincia);
    cargarOpciones(distrito, filasProvincia.map((oferta) => oferta.dataset.distrito), "Todos los distritos");
  };

  const filtrar = () => {
    const seleccion = {
      departamento: departamento.value,
      provincia: provincia.value,
      distrito: distrito.value,
    };
    let visibles = 0;

    ofertas.forEach((oferta) => {
      const coincide = Object.entries(seleccion).every(([campo, valor]) => !valor || oferta.dataset[campo] === valor);
      oferta.hidden = !coincide;
      if (coincide) visibles += 1;
    });

    secciones.forEach((seccion) => {
      seccion.hidden = !seccion.querySelector(".job-item:not([hidden])");
    });
    contador.textContent = `${visibles} ${visibles === 1 ? "oferta encontrada" : "ofertas encontradas"}.`;
    vacio.hidden = visibles !== 0;
  };

  departamento.addEventListener("change", () => {
    provincia.value = "";
    distrito.value = "";
    actualizarControles();
    filtrar();
  });
  provincia.addEventListener("change", () => {
    distrito.value = "";
    actualizarControles();
    filtrar();
  });
  distrito.addEventListener("change", filtrar);
  limpiar.addEventListener("click", () => {
    departamento.value = "";
    provincia.value = "";
    distrito.value = "";
    actualizarControles();
    filtrar();
    departamento.focus();
  });

  actualizarControles();
  filtrar();
})();

(() => {
  const departamento = document.querySelector("#filtro-departamento");
  const provincia = document.querySelector("#filtro-provincia");
  const distrito = document.querySelector("#filtro-distrito");
  const busqueda = document.querySelector("#buscar-ofertas");
  const orden = document.querySelector("#orden-ofertas");
  const limpiar = document.querySelector("#limpiar-filtros");
  const verGuardados = document.querySelector("#ver-guardados");
  const cantidadGuardados = document.querySelector("#cantidad-guardados");
  const contador = document.querySelector("#contador-resultados");
  const vacio = document.querySelector("#resultados-vacios");
  const ofertas = [...document.querySelectorAll(".job-item")];
  const secciones = [...document.querySelectorAll(".dep-section")];
  const chips = [...document.querySelectorAll(".district-chip")];
  const claveGuardados = "empleos-canete-guardados";

  if (!departamento || !provincia || !distrito || !busqueda || !orden || !limpiar || !contador || !vacio || !ofertas.length) return;

  const normalizar = (texto) =>
    String(texto || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("es")
      .trim();

  const leerGuardados = () => {
    try {
      return new Set(JSON.parse(localStorage.getItem(claveGuardados) || "[]"));
    } catch {
      return new Set();
    }
  };

  let guardados = leerGuardados();
  let soloGuardados = false;

  const guardarPreferencias = () => {
    localStorage.setItem(claveGuardados, JSON.stringify([...guardados]));
  };

  const actualizarGuardados = () => {
    ofertas.forEach((oferta) => {
      const boton = oferta.querySelector(".favorite-toggle");
      const activo = guardados.has(oferta.dataset.id);
      if (!boton) return;
      boton.textContent = activo ? "★" : "☆";
      boton.classList.toggle("active", activo);
      boton.setAttribute("aria-pressed", String(activo));
      boton.title = activo ? "Quitar de guardados" : "Guardar oferta";
    });
    if (cantidadGuardados) cantidadGuardados.textContent = String(guardados.size);
  };

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

  const ordenarOfertas = () => {
    const campo = orden.value === "empresa" ? "entidad" : "titulo";
    secciones.forEach((seccion) => {
      const lista = seccion.querySelector(".job-list");
      if (!lista) return;
      [...lista.children]
        .sort((a, b) => a.dataset[campo].localeCompare(b.dataset[campo], "es", { sensitivity: "base" }))
        .forEach((oferta) => lista.appendChild(oferta));
    });
  };

  const actualizarChips = () => {
    chips.forEach((chip) => chip.classList.toggle("active", chip.dataset.distrito === distrito.value));
  };

  const filtrar = () => {
    const texto = normalizar(busqueda.value);
    const seleccion = {
      departamento: departamento.value,
      provincia: provincia.value,
      distrito: distrito.value,
    };
    let visibles = 0;

    ofertas.forEach((oferta) => {
      const coincideUbicacion = Object.entries(seleccion).every(
        ([campo, valor]) => !valor || oferta.dataset[campo] === valor,
      );
      const contenido = normalizar(`${oferta.dataset.titulo} ${oferta.dataset.entidad} ${oferta.dataset.distrito}`);
      const coincideTexto = !texto || contenido.includes(texto);
      const coincideGuardado = !soloGuardados || guardados.has(oferta.dataset.id);
      const visible = coincideUbicacion && coincideTexto && coincideGuardado;
      oferta.hidden = !visible;
      if (visible) visibles += 1;
    });

    secciones.forEach((seccion) => {
      const tieneResultados = Boolean(seccion.querySelector(".job-item:not([hidden])"));
      const sinOfertas = !seccion.querySelector(".job-item");
      const distritoSeccion = seccion.dataset.seccionDistrito;
      const mostrarSeccionVacia =
        sinOfertas &&
        !texto &&
        !soloGuardados &&
        (!distrito.value || distrito.value === distritoSeccion);
      seccion.hidden = !tieneResultados && !mostrarSeccionVacia;
      if (tieneResultados && (texto || distrito.value || soloGuardados)) {
        const lista = seccion.querySelector(".job-list");
        const boton = seccion.querySelector(".district-heading");
        if (lista && boton) {
          lista.hidden = false;
          boton.setAttribute("aria-expanded", "true");
          const icono = boton.querySelector(".toggle-icon");
          if (icono) icono.textContent = "−";
        }
      }
    });

    contador.textContent = `${visibles} ${visibles === 1 ? "oferta encontrada" : "ofertas encontradas"}.`;
    vacio.hidden = visibles !== 0 || (!texto && !soloGuardados && Boolean(distrito.value));
    actualizarChips();
  };

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      distrito.value = chip.dataset.distrito;
      soloGuardados = false;
      if (verGuardados) {
        verGuardados.classList.remove("active");
        verGuardados.setAttribute("aria-pressed", "false");
      }
      filtrar();
      contador.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  ofertas.forEach((oferta) => {
    const boton = oferta.querySelector(".favorite-toggle");
    boton?.addEventListener("click", () => {
      const id = oferta.dataset.id;
      guardados.has(id) ? guardados.delete(id) : guardados.add(id);
      guardarPreferencias();
      actualizarGuardados();
      if (soloGuardados) filtrar();
    });
  });

  secciones.forEach((seccion) => {
    const boton = seccion.querySelector(".district-heading");
    const lista = seccion.querySelector(".job-list");
    boton?.addEventListener("click", () => {
      const abierto = boton.getAttribute("aria-expanded") === "true";
      boton.setAttribute("aria-expanded", String(!abierto));
      lista.hidden = abierto;
      const icono = boton.querySelector(".toggle-icon");
      if (icono) icono.textContent = abierto ? "+" : "−";
    });
  });

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
  busqueda.addEventListener("input", filtrar);
  orden.addEventListener("change", () => {
    ordenarOfertas();
    filtrar();
  });
  verGuardados?.addEventListener("click", () => {
    soloGuardados = !soloGuardados;
    verGuardados.classList.toggle("active", soloGuardados);
    verGuardados.setAttribute("aria-pressed", String(soloGuardados));
    filtrar();
  });
  limpiar.addEventListener("click", () => {
    departamento.value = "";
    provincia.value = "";
    distrito.value = "";
    busqueda.value = "";
    soloGuardados = false;
    if (verGuardados) {
      verGuardados.classList.remove("active");
      verGuardados.setAttribute("aria-pressed", "false");
    }
    actualizarControles();
    filtrar();
    busqueda.focus();
  });

  actualizarControles();
  ordenarOfertas();
  actualizarGuardados();
  filtrar();
})();

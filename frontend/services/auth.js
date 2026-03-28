// Servicio de autenticación para gestionar el login y registro de usuarios
const BASE_API = window.location.origin;

// Clave para almacenar el usuario actual en localStorage
const CLAVE_USUARIO_ACTUAL = "greenlabCurrentUser";
// Reglas de validación para la contraseña
const REGLAS_CONTRASENA = {
  longitud: (valor) => valor.length >= 8,
  mayuscula: (valor) => /[A-ZÁÉÍÓÚÜÑ]/.test(valor),
  minuscula: (valor) => /[a-záéíóúüñ]/.test(valor),
  numero: (valor) => /\d/.test(valor),
  especial: (valor) => /[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]/.test(valor),
};
// Función para mostrar mensajes de éxito o error en los formularios
function mostrarMensajeFormulario(elemento, mensaje, tipo) {
  if (!elemento) {
    return;
  }

  elemento.textContent = mensaje || "";
  elemento.classList.remove(
    "mensaje-formulario--exito",
    "mensaje-formulario--error",
  );

  if (tipo) {
    elemento.classList.add(
      tipo === "exito"
        ? "mensaje-formulario--exito"
        : "mensaje-formulario--error",
    );
  }
}
// Función para mostrar avisos específicos en campos del formulario
function mostrarAvisoCampo(campo, mensaje) {
  if (!campo) {
    return;
  }

  campo.classList.toggle("campo--invalido", Boolean(mensaje));

  let aviso = campo.querySelector(".aviso-campo");
  if (!mensaje) {
    aviso?.remove();
    return;
  }

  if (!aviso) {
    aviso = document.createElement("p");
    aviso.className = "aviso-campo";
    campo.append(aviso);
  }

  aviso.textContent = mensaje;
}
// Función para limpiar avisos de campos específicos
function limpiarAvisoCampo(campo) {
  mostrarAvisoCampo(campo, "");
}
// Función para validar campos obligatorios en el formulario de registro
function validarCamposObligatoriosRegistro(formulario) {
  const camposObligatorios = ["nombre", "email", "password"];
  const camposVacios = [];

  for (const nombre of camposObligatorios) {
    const input = formulario.elements.namedItem(nombre);
    const campo = input?.closest(".campo");
    const valor = String(input?.value || "").trim();
    const estaVacio = !valor;

    limpiarAvisoCampo(campo);
    campo?.classList.toggle("campo--invalido", estaVacio);
    if (estaVacio) {
      camposVacios.push(nombre);
    }
  }

  return camposVacios;
}
// Función para decorar el título principal con spans para cada letra
function decorarTituloPrincipal() {
  const titulos = document.querySelectorAll(
    "body[data-pagina] .panel-visual h1",
  );

  for (const titulo of titulos) {
    if (titulo.dataset.decorado === "true") {
      continue;
    }

    const textoOriginal = titulo.textContent || "";
    titulo.dataset.decorado = "true";
    titulo.setAttribute("aria-label", textoOriginal.trim());
    titulo.textContent = "";

    const partes = textoOriginal.split(/(\s+)/);
    for (const parte of partes) {
      if (!parte) {
        continue;
      }

      if (/^\s+$/.test(parte)) {
        titulo.append(document.createTextNode(parte));
        continue;
      }

      const palabra = document.createElement("span");
      palabra.className = "palabra-titulo";
      palabra.setAttribute("aria-hidden", "true");

      for (const caracter of Array.from(parte)) {
        const letra = document.createElement("span");
        letra.className = "letra-titulo";
        letra.textContent = caracter;
        palabra.append(letra);
      }

      titulo.append(palabra);
    }
  }
}
// Función para sincronizar el estado de visibilidad de la contraseña con los atributos ARIA del botón
function sincronizarEstadoContrasena(boton, input) {
  const esVisible = input.type === "text";
  boton.setAttribute("aria-pressed", String(esVisible));
  boton.setAttribute(
    "aria-label",
    esVisible ? "Ocultar contraseña" : "Mostrar contraseña",
  );
}
// Función para alternar la visibilidad de la contraseña al hacer clic en el botón
function alternarVisibilidadContrasena(boton) {
  const input = document.getElementById(boton.dataset.contrasenaObjetivo || "");
  if (!input) {
    return;
  }

  input.type = input.type === "text" ? "password" : "text";
  sincronizarEstadoContrasena(boton, input);
}
// Función para actualizar la lista de requisitos de contraseña cumplidos o no
function actualizarRequisitosContrasena(contrasena) {
  const requisitos = document.querySelectorAll(
    "#requisitos-contrasena .item-requisito",
  );
  if (!requisitos.length) {
    return;
  }

  for (const requisito of requisitos) {
    const nombreRegla = requisito.dataset.regla;
    const cumple = Boolean(REGLAS_CONTRASENA[nombreRegla]?.(contrasena));
    requisito.classList.toggle("item-requisito--cumplido", cumple);
  }
}
// Función para verificar si la contraseña cumple con todas las reglas establecidas
function contrasenaCumpleTodosLosRequisitos(contrasena) {
  return Object.values(REGLAS_CONTRASENA).every((regla) => regla(contrasena));
}
// Funciones para obtener mensajes de error específicos según el estado HTTP y la respuesta del backend al intentar iniciar sesión
function obtenerMensajeErrorLogin(estado, datos) {
  if (datos?.message) {
    return datos.message;
  }
  if (estado === 400) {
    return "Completa el correo y la contraseña.";
  }
  if (estado === 401) {
    return "Correo o contraseña incorrectos.";
  }
  return "No se pudo iniciar sesión.";
}

function obtenerMensajeErrorRegistro(estado, datos) {
  if (datos?.message) {
    return datos.message;
  }
  if (estado === 409) {
    return "Ya existe un usuario con ese correo.";
  }
  if (estado === 400) {
    return "Revisa los campos obligatorios y la contraseña.";
  }
  return "No se pudo crear el usuario.";
}
// Función para enviar una solicitud POST con JSON al backend y manejar la respuesta
async function enviarJson(url, carga) {
  const respuesta = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(carga),
  });

  const datos = await respuesta.json().catch(() => ({}));
  return { respuesta, datos };
}
// Funciones para gestionar el proceso de inicio de sesión o registro al enviar el formulario correspondiente
async function gestionarLogin(evento) {
  evento.preventDefault();
  const formulario = evento.currentTarget;
  const mensaje = document.getElementById("mensaje-login");
  const datosFormulario = new FormData(formulario);
  const carga = {
    email: datosFormulario.get("email"),
    password: datosFormulario.get("password"),
  };

  mostrarMensajeFormulario(mensaje, "Validando acceso...", null);

  try {
    const { respuesta, datos } = await enviarJson(
      `${BASE_API}/api/login`,
      carga,
    );
    if (!respuesta.ok || !datos.ok) {
      mostrarMensajeFormulario(
        mensaje,
        obtenerMensajeErrorLogin(respuesta.status, datos),
        "error",
      );
      return;
    }

    localStorage.setItem(CLAVE_USUARIO_ACTUAL, JSON.stringify(datos.data));
    mostrarMensajeFormulario(
      mensaje,
      `Bienvenido, ${datos.data.nombre}. Inicio de sesión correcto.`,
      "exito",
    );
  } catch (error) {
    mostrarMensajeFormulario(
      mensaje,
      "No se pudo contactar con el backend Flask.",
      "error",
    );
  }
}

async function gestionarRegistro(evento) {
  evento.preventDefault();
  const formulario = evento.currentTarget;
  const mensaje = document.getElementById("mensaje-registro");
  const datosFormulario = new FormData(formulario);
  const contrasena = String(datosFormulario.get("password") || "");
  const carga = {
    nombre: datosFormulario.get("nombre"),
    email: datosFormulario.get("email"),
    password: contrasena,
    rol: "personal_laboratorio",
  };

  const camposVacios = validarCamposObligatoriosRegistro(formulario);
  if (camposVacios.length) {
    mostrarMensajeFormulario(
      mensaje,
      "Completa los campos obligatorios.",
      "error",
    );
    return;
  }

  if (!contrasenaCumpleTodosLosRequisitos(contrasena)) {
    mostrarAvisoCampo(
      formulario.elements.namedItem("password")?.closest(".campo"),
      "La contraseña no cumple los requisitos obligatorios.",
    );
    mostrarMensajeFormulario(
      mensaje,
      "La contraseña no cumple todos los requisitos obligatorios.",
      "error",
    );
    return;
  }

  mostrarMensajeFormulario(mensaje, "Creando cuenta...", null);

  try {
    const { respuesta, datos } = await enviarJson(
      `${BASE_API}/api/usuarios`,
      carga,
    );

    if (!respuesta.ok || !datos.ok) {
      mostrarMensajeFormulario(
        mensaje,
        obtenerMensajeErrorRegistro(respuesta.status, datos),
        "error",
      );
      return;
    }

    mostrarMensajeFormulario(
      mensaje,
      "Cuenta creada correctamente. Redirigiendo al acceso...",
      "exito",
    );
    formulario.reset();

    for (const campo of formulario.querySelectorAll(".campo")) {
      limpiarAvisoCampo(campo);
    }

    actualizarRequisitosContrasena("");
    window.setTimeout(() => {
      window.location.href = "/login";
    }, 900);
  } catch (error) {
    mostrarMensajeFormulario(
      mensaje,
      "No se pudo contactar con el backend Flask.",
      "error",
    );
  }
}
// Función para enlazar los botones de alternar visibilidad de contraseña con sus respectivos campos y sincronizar su estado
function enlazarAlternadoresContrasena() {
  for (const boton of document.querySelectorAll("[data-contrasena-objetivo]")) {
    const input = document.getElementById(
      boton.dataset.contrasenaObjetivo || "",
    );
    if (!input) {
      continue;
    }

    sincronizarEstadoContrasena(boton, input);
    boton.addEventListener("click", () => alternarVisibilidadContrasena(boton));
  }
}
// Función para enlazar el campo de contraseña del formulario de registro con la actualización en tiempo real del cumplimiento de los requisitos
function enlazarRequisitosContrasena() {
  const inputContrasena = document.getElementById("contrasena-registro");
  if (!inputContrasena) {
    return;
  }

  const sincronizarRequisitos = () =>
    actualizarRequisitosContrasena(inputContrasena.value);

  sincronizarRequisitos();
  inputContrasena.addEventListener("input", sincronizarRequisitos);
}
// Función para enlazar los formularios de login y registro con sus respectivas funciones de gestión al enviar, así como para limpiar avisos específicos al modificar los campos
function enlazarFormularios() {
  const formularioLogin = document.getElementById("formulario-login");
  if (formularioLogin) {
    formularioLogin.addEventListener("submit", gestionarLogin);
  }

  const formularioRegistro = document.getElementById("formulario-registro");
  if (formularioRegistro) {
    formularioRegistro.addEventListener("submit", gestionarRegistro);
    formularioRegistro.addEventListener("input", (evento) => {
      const input = evento.target;
      if (!(input instanceof HTMLInputElement)) {
        return;
      }

      const campo = input.closest(".campo");
      if (!campo) {
        return;
      }

      if (String(input.value || "").trim()) {
        limpiarAvisoCampo(campo);
      }
    });
  }
}

window.addEventListener("DOMContentLoaded", () => {
  decorarTituloPrincipal();
  enlazarAlternadoresContrasena();
  enlazarRequisitosContrasena();
  enlazarFormularios();
});

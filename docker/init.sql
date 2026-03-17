USE greenlab;

DROP TABLE IF EXISTS checklist_entry_items;
DROP TABLE IF EXISTS checklist_entries;
DROP TABLE IF EXISTS checklist_template_items;
DROP TABLE IF EXISTS checklist_templates;
DROP TABLE IF EXISTS issues;
DROP TABLE IF EXISTS equipment;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(120) NOT NULL,
  email VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  rol ENUM('jefe_laboratorio', 'personal_laboratorio') NOT NULL DEFAULT 'personal_laboratorio',
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email)
);

CREATE TABLE equipment (
  id INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(150) NOT NULL,
  tipo VARCHAR(100) NOT NULL,
  ubicacion VARCHAR(120) NOT NULL,
  temp_objetivo DECIMAL(5, 2),
  responsable_id INT,
  frecuencia_mantenimiento VARCHAR(50) NOT NULL,
  ultima_revision DATE,
  PRIMARY KEY (id),
  CONSTRAINT fk_equipment_responsable
    FOREIGN KEY (responsable_id) REFERENCES users(id)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);

CREATE TABLE checklist_templates (
  id INT NOT NULL AUTO_INCREMENT,
  equipment_type VARCHAR(100) NOT NULL,
  nombre VARCHAR(150) NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE checklist_template_items (
  id INT NOT NULL AUTO_INCREMENT,
  template_id INT NOT NULL,
  item_texto VARCHAR(255) NOT NULL,
  obligatorio TINYINT(1) NOT NULL DEFAULT 1,
  orden INT NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  CONSTRAINT fk_template_items_template
    FOREIGN KEY (template_id) REFERENCES checklist_templates(id)
    ON DELETE CASCADE
);

CREATE TABLE checklist_entries (
  id INT NOT NULL AUTO_INCREMENT,
  equipment_id INT NOT NULL,
  user_id INT NOT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  comentario TEXT,
  PRIMARY KEY (id),
  CONSTRAINT fk_entries_equipment
    FOREIGN KEY (equipment_id) REFERENCES equipment(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_entries_user
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE checklist_entry_items (
  id INT NOT NULL AUTO_INCREMENT,
  entry_id INT NOT NULL,
  template_item_id INT NOT NULL,
  valor ENUM('correcto', 'incorrecto', 'no_aplica') NOT NULL DEFAULT 'correcto',
  observacion VARCHAR(255),
  PRIMARY KEY (id),
  CONSTRAINT fk_entry_items_entry
    FOREIGN KEY (entry_id) REFERENCES checklist_entries(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_entry_items_template_item
    FOREIGN KEY (template_item_id) REFERENCES checklist_template_items(id)
);

CREATE TABLE issues (
  id INT NOT NULL AUTO_INCREMENT,
  equipment_id INT NOT NULL,
  user_id INT NOT NULL,
  titulo VARCHAR(150) NOT NULL,
  descripcion TEXT NOT NULL,
  prioridad ENUM('baja', 'media', 'alta', 'critica') NOT NULL DEFAULT 'media',
  estado ENUM('abierta', 'en_proceso', 'cerrada') NOT NULL DEFAULT 'abierta',
  creado_a DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cerrado_a DATETIME,
  PRIMARY KEY (id),
  CONSTRAINT fk_issues_equipment
    FOREIGN KEY (equipment_id) REFERENCES equipment(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_issues_user
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT INTO users (nombre, email, password_hash, rol) VALUES
('Dra. Elena Martin', 'elena@greenlab.local', 'scrypt:32768:8:1$l2ank37gcrunril4$95686d452a36adcb047e6e48204349701ba3938df179e16d64f33aeef4ab8a8cf2e54baac5994edef59087db21000c0720688e4dae30975bf2d7f5c68462872b', 'jefe_laboratorio'),
('Carlos Ruiz', 'carlos@greenlab.local', 'scrypt:32768:8:1$aLl112N1FuDbyfQH$1d18935787d2c4502012c90a7461439789b91930569652a8b1d7b071101f50316930f9dfa99dd083192fe9dc0012c05d5af45046352ba12ed473b9e4cfcc5bec', 'personal_laboratorio'),
('Lucia Gomez', 'lucia@greenlab.local', 'scrypt:32768:8:1$3XjNJ98Xajh0pap2$dd04f8f9aa207c10cfc295edb473a25fc723b168fa5e8cadc1614bf7b890d2fa57958eb106d2141d9db9ec070b6fe53ce8c4f25536ac1bacf7cdcef8a5209f26', 'personal_laboratorio');

INSERT INTO equipment (nombre, tipo, ubicacion, temp_objetivo, responsable_id, frecuencia_mantenimiento, ultima_revision) VALUES
('UltraCongelador UF-01', 'ultracongelador', 'Sala Frio A', -80.00, 1, 'mensual', '2026-02-01'),
('Incubadora INC-02', 'incubadora', 'Sala Cultivos B', 37.00, 2, 'trimestral', '2026-01-15'),
('Centrifuga CEN-03', 'centrifuga', 'Sala Procesado C', NULL, 3, 'mensual', '2026-02-10');

INSERT INTO checklist_templates (equipment_type, nombre) VALUES
('ultracongelador', 'Revision diaria ultracongelador'),
('incubadora', 'Revision diaria incubadora');

INSERT INTO checklist_template_items (template_id, item_texto, obligatorio, orden) VALUES
(1, 'Temperatura dentro del rango', 1, 1),
(1, 'Sin alarma activa', 1, 2),
(1, 'Puerta cierra correctamente', 1, 3),
(2, 'Temperatura en 37C', 1, 1),
(2, 'Bandejas limpias', 1, 2);

INSERT INTO checklist_entries (equipment_id, user_id, fecha, comentario) VALUES
(1, 2, '2026-02-20 08:15:00', 'Revision correcta sin incidencias'),
(2, 3, '2026-02-20 09:10:00', 'Se observa cierre algo duro');

INSERT INTO checklist_entry_items (entry_id, template_item_id, valor, observacion) VALUES
(1, 1, 'correcto', ''),
(1, 2, 'correcto', ''),
(1, 3, 'correcto', ''),
(2, 4, 'correcto', ''),
(2, 5, 'incorrecto', 'Pendiente limpieza al final del turno');

INSERT INTO issues (equipment_id, user_id, titulo, descripcion, prioridad, estado, creado_a, cerrado_a) VALUES
(2, 3, 'Cierre de puerta duro', 'La puerta necesita fuerza extra para cerrar', 'media', 'abierta', '2026-02-20 09:20:00', NULL),
(1, 2, 'Alarma puntual de temperatura', 'Alarma breve durante 2 minutos', 'alta', 'en_proceso', '2026-02-19 07:55:00', NULL),
(3, 2, 'Vibracion anomala', 'Vibracion superior a la habitual', 'media', 'cerrada', '2026-02-18 12:00:00', '2026-02-19 16:30:00');

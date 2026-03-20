Prueba de conexión

    -Levantamos la conexión:
    ![alt text](image.png)

    -Curl para comprobar el estado de conexión (ok = está bien):
    ![alt text](image-1.png)

    -Prueba obtención (GET) de datos desde la base de datos:
    ![alt text](image-2.png)
    ![alt text](image-3.png)

    -Prueba (POST): Requerimiento previo es configurar los datos que se pretenden insertar dentro del archivo payload.json para las pruebas --> curl.exe -X POST "http://localhost:5000/api/usuarios" -H "Content-Type: application/json" --data-binary "@payload.json":
    ![alt text](image-4.png)
    ![alt text](image-5.png)

    -Prueba (PUT):
    ![alt text](image-6.png)
    ![alt text](image-7.png)

    -Prueba (DELETE);
    ![alt text](image-8.png)
    ![alt text](image-9.png)


    -Prueba (POST) de login --> se pide emial y password
    ![alt text](image-10.png)


    ![alt text](image-11.png)
    ![alt text](image-12.png)


    -Prueba arranque aplicación con Flask:
    ![alt text](image-13.png)

    Comando utilizado:
    python -m flask --app app.py run --debug
    Da error porque apunta a la anterior versión de la app que se llamaba TriaGe.

    Este comando sirve para iniciar el servidor de desarrollo de Flask cargando la aplicación definida en `app.py` lo que permite recarga automática al guardar cambios y muestra detallada de errores durante el desarrollo.

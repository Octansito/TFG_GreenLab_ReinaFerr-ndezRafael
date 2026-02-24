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

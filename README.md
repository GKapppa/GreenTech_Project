#MENTOR IA - GreenTech Project 🤖🤖

#NOTA: EL PROMPT DEBE SER HECHO EN ESPANOL

Sistema de asistencia inteligente basado en RAG (Retrieval-Augmented Generation) para la "Empresa" GreenTech

#Caracteristicas

**IA GENERATIVA** Uso de modelos de lenguaje via groq.
**BASE DE DATOS** Vector store esta en MongoDB Atlas.
**Containers** Listos para desplegar con docker.
**Seguridad** Gestion de variables de entorno mediante `.env` estas estan excluidas del repo.

#Instrucciones de instalacion y uso
1. **Clonar el repositorio:**
git clone [https://github.com/GKapppa/GreenTech_Project.git](https://github.com/GKapppa/GreenTech_Project.git)

#Levantar docker
**Construir la imagen**
```bash
docker build -t mentoria-greentech .
```

**Ejecutar contenedor**
```bash
docker run -p 8502:8501 --env-file .env mentoria-greentech
```

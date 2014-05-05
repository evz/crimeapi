from crimeapi import create_app, make_celery
app = create_app()
celery_app = make_celery(app)

if __name__ == "__main__":
    app.run(debug=True)

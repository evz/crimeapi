from crimeapi import create_app, make_celery
app = create_app()
celery_app = make_celery(app)
app.run(debug=True)

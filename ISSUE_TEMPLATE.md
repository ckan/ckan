# Submitting a CKAN issue

Do not use an issue to ask how to do something - for that use [Stack Overflow]http://stackoverflow.com/questions/tagged/ckan).
If you don’t get a quick response (over 48 business hours) on Stack Overflow then please email the issue URL to the [ckan-dev mailing list]https://lists.okfn.org/mailman/listinfo/ckan-dev).


## Describe what went wrong

Tell us what you were doing when it went wrong.

```
Fill me in
```


## Steps to recreate the problem.

Provide a comprehensive step-by-step guide to reproduce the issue. If it's related to an API call, provide the API call. A screenshot is often helpful.

```
Fill me in
```


## The supporting information

If it is a 500 error / ServerError / exception then it’s essential to supply the full stack trace provided in the CKAN log. Such logs can be found in /var/log/apache2/ (particularly *.error.log)

```
Fill me in
```


## Platform and software versions

Please run the following commands on the server you're running CKAN on:


**$ cat /etc/lsb-release**

```
Fill me in
```

**$ curl http://PUT_YOUR_URL_HERE/api/util/status**

```
Fill me in
```

## Other comments?

Anything else we should know?


```
Optionally fill me in
```


## Checklist

Thanks for reporting an issue! Please make sure you you complete the checklist below:

- [ ] You are not asking a question about how to do something,
- [ ] You have checked that a similar issue does not already exist or has been closed before,
- [ ] You have provided a descriptive title,
- [ ] You have provided all the requested missing information,
- [ ] You have provided all supporting supporting information such as links, files, logs and, or screenshots, and
- [ ] You have provided the versions of your operating system, CKAN, extensions and other important components.

### REQUIREMENT

This Project is to download 20 preview images of a random camera from demo account by using Eagle Eye Networks API. Use python with GEvent to download image concurrently using 5 worker greenlets.

**API Docs**: [https://apidocs.eagleeyenetworks.com/apidocs](https://apidocs.eagleeyenetworks.com/apidocs) 

### PROJECT BRIFE

Under the `EENProject` directory.
- `eenDownload.py`, which is main python file, to complete the above requirement.
- `out` folder, to storage the download preview images here.

### ENVIRONEMNT

I am doing the project in my Macbook Pro. So the environment should be:

- macOS Mojave 10.14.2
- Python 3.6.3
- gevent 1.4.0

#### how to run the code

First of all, if you like, you could modify the variable `STORAGE_FILE_DIR` to the path where you want to store the images.

Open the terminal and go to the `/EENProject` directory, using command `$python3 eenDownload.py` to run the program. Or you can open the project in your Python IDE, run the code within it. Both methods can be used.

### PROCESS

To get the preview images from a random camera, here are five steps:
1. Authenticate with username and password. 
2. Authorize with the token returned by Authenticate.
3. Get camera list.
4. Check whether the camera is able to download image in the camera list.
5. Using GEvent to download camera preview images.

I will explain every step what I am doing.

##### Step 1: Authenticate with username and password

Interactive URL: **https://login.eagleeyenetworks.com/g/aaa/authenticate**  
Method: **POST**

In this step, we should bring username and password , send a POST request to the above URL in order to get Authenticate Token. Normally here should take the API Key too, but we are just demo account, does not need to use API Key in this project.

*Reverence API Docs for this step: https://apidocs.eagleeyenetworks.com/apidocs/#1-authenticate* 

##### Step 2: Authorize

Interactive URL:
**https://login.eagleeyenetworks.com/g/aaa/authorize**  
Method: **POST**

Also send a POST to above URL, bring the `Token` which we get from step 1. This step is to get authorized by the system. In the response, the most important two things are `active_brand_subdomain` and `auth_key` in cookies.

*Reverence API Docs for this step: https://apidocs.eagleeyenetworks.com/apidocs/#3-authorize*

##### Step 3: Get Camera List
Interactive URL:
**https://[active_brand_subdomain].eagleeyenetworks.com/g/device/list**  
Method:**GET**  

The url has been a little changed here. We use `active_brand_subdomain`, which comes from step 2, as domain, so that response speed will be faster and reduce stress on server.  

Using a GET method request to get all bridge information from server. There are a lot kinds of devices in this list. We should clean the list and pick out the available cameras as a list for next step.

Those are not available camera:
- **Device Type** is not `camera`, which is 3rd value in camera info list.
- **is_unsupported** value is `NOT supported(1)`, which is 13th value in camera info list.
- **Camera ID** value is `None`, which is 2nd value in camera info list.

After picking out the available cameras, we should shuffle the list in order to download image from a random camera.

*Reverence API Docs for this step: https://apidocs.eagleeyenetworks.com/apidocs/#get-list-of-cameras  
https://apidocs.eagleeyenetworks.com/apidocs/#3-authorize*


##### Step 4: Check whether the camera is able to download image

Interactive URL:
**https://[active_brand_subdomain].eagleeyenetworks.com/asset/asset/image.jpeg**  
Method:**GET**  

Although we have picked up the available camera list by above three restrictive conditions, some cameras are still not able to support download image.

Camera may suddenly be offline after you pick it up or some other strange things happened. To overcome those 'happened things' and make sure that we can successfully get 20 images from a camera, we should add a check method here to pick up one most health camera and download its images.

*Reverence API Docs for this step: https://apidocs.eagleeyenetworks.com/apidocs/#get-image*

##### Step 5: Download Image With GEvent

Interactive URL:
**https://[active_brand_subdomain].eagleeyenetworks.com/asset/asset/image.jpeg**  
Method:**GET**  

The interactive URL and request method are the same as the previous step. But here we use GEvent to implement concurrently download. Two requirements, concurrent downloading and 5 greenlets work in same time.

Here I use GEvent.pool to create a pool which size is 5. So that the number of worker greenlets in concurrently downloading is five at a time.

There is a fault tolerant I used here is that I create more than 20 greenlets here. In case of download image request failed. Here I choose to create 30 greenlets. For example, there are 4 of 20 download image requests failed by some reason. We still have 10 backup greenlets can use to continue downloading until we get 20 pictures. The total number is not fixed, here I just choose 30.

The control flow of terminate is that I use a global variables named `finished` to shutdown GEvent pool if we have got 20 images.

*Reverence API Docs for this step: https://apidocs.eagleeyenetworks.com/apidocs/#get-image  
http://www.gevent.org/*

After finish those five steps, we can get 20 preview images of a random camera and storage them into local disk.

Here is fist time running and get 20 pictures:

![first_time_run](https://raw.githubusercontent.com/SwyftG/NewStanderJapanses/master/image/first_time_run.png)

Then the second time running, we get the different 20 pictures:

![second_time_run](https://raw.githubusercontent.com/SwyftG/NewStanderJapanses/master/image/second_time_run.png)


Compare those two running result:

![compare_result](https://raw.githubusercontent.com/SwyftG/NewStanderJapanses/master/image/compare_result.png)

Here is running log:

![log_1](https://raw.githubusercontent.com/SwyftG/NewStanderJapanses/master/image/log_1.png)

![log_2](https://raw.githubusercontent.com/SwyftG/NewStanderJapanses/master/image/log_2.png)


### UNSOLVED PROBLEMS

During coding,  I got a length of 94 bridge list in step 3. I know that they are not all available camera although they are from API `eagleeyenetworks.com/g/device/list`. 

I list out the unavailable camera data below, the number is thier index and error message if download it. Sorry about not listing the camera ID, because it is not easy to type in here. 

##### Not A Cameras(device type):

Index: 9, 16, 23, 38, 67, 69, 73, 83, 86, 93

Error Message: esn not a camera

##### Not Supported Cameras(Not-support is 1):
Index: 8, 19, 40, 64, 87, 88

Error Message: something like 'proxy destination node connect timeout'

##### Camera ID is None:
Index: 94
Error Message: Invalid Camera ID (c= or id=)

There are still a number of cameras which is not available to download images, there indices are:

25, 32, 44, 52, 55, 68, 72, 77

Their error message are two kinds:
1. 'no matching asset'
2. something like 'proxy destination node connect timeout'

I have logged in `https://login.eagleeyenetworks.com/` and see those cameras in centro control web browser. Found out some of them are **OFF**. So I came back to my code and try to find out how I can know whether the camera is ON or OFF. I used debug mode to find out. Their data shows same as other working cameras unless the **devices_status**. 

I try to figure out the mystery of Bitmask, read the `https://apidocs.eagleeyenetworks.com/apidocs/#status-bitmask` documents, but still do not know how to check it.

For example, the index 25 camera, which devices_status value is 32803, obviously it an Integer. I changed it to hex, and did not find any corresponding number here.

This problem has troubled me for a long time. I still do not have solution for it.

**In order to complete the task and make sure that the program is strong, I add a check_camera method in the program, to check whether the camera can be visited or not.**


### AT LAST THANKS

Thank Eagle Eye Networks for giving me this wonderful opportunity. This programming test is really reasonable and fun. I learn a lot of things from it, and have experience of using Eagle Eye Networks API. The API is so powerful, interesting and great to use.

Thank you very much. If you have any questions, please feel free to contact me via email.

Emaill: gaoliangcode@gmail.com
#!/bin/bash
{
	sh ./light_delete.sh;
	echo "light_delete success";

	sh ./expression_delete.sh;
	echo "expression_delete success";

	sh ./camera_delete.sh;
	echo "camera_delete success";
}
